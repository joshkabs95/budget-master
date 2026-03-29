import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.transactions.models import Transaction
from .matcher import match
from .models import ReconciliationSession, ReconciliationEntry
from .serializers import ReconciliationSessionSerializer


def _parse_bank_csv(content: str) -> list[dict]:
    """
    Parse a bank CSV. Tries common French bank formats.
    Expected columns (flexible): Date, Libellé/Label, Montant/Débit/Crédit
    """
    lines = []
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    if not reader.fieldnames:
        reader = csv.DictReader(io.StringIO(content), delimiter=',')

    for row in reader:
        # Normalize field names
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}

        # Date
        raw_date = (
            normalized.get('date') or normalized.get('date opération') or
            normalized.get('date operation') or normalized.get('dateop') or ''
        )
        parsed_date = None
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y'):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except (ValueError, TypeError):
                continue
        if not parsed_date:
            continue

        # Label
        label = (
            normalized.get('libellé') or normalized.get('libelle') or
            normalized.get('label') or normalized.get('description') or
            normalized.get('opération') or normalized.get('operation') or ''
        )

        # Amount — try Montant first, then Débit/Crédit
        raw_amount = (
            normalized.get('montant') or normalized.get('amount') or
            normalized.get('montant opération') or ''
        )
        amount = None
        if raw_amount:
            try:
                amount = Decimal(raw_amount.replace(' ', '').replace(',', '.').replace('\xa0', ''))
            except InvalidOperation:
                pass

        if amount is None:
            # Try debit/credit columns
            debit_raw = normalized.get('débit') or normalized.get('debit') or '0'
            credit_raw = normalized.get('crédit') or normalized.get('credit') or '0'
            try:
                debit = Decimal(debit_raw.replace(' ', '').replace(',', '.').replace('\xa0', '') or '0')
                credit = Decimal(credit_raw.replace(' ', '').replace(',', '.').replace('\xa0', '') or '0')
                amount = credit - debit if credit or debit else None
            except InvalidOperation:
                pass

        if amount is None:
            continue

        lines.append({'date': parsed_date, 'label': label, 'amount': amount})

    return lines


class ReconciliationViewSet(viewsets.ModelViewSet):
    serializer_class = ReconciliationSessionSerializer

    def get_queryset(self):
        return ReconciliationSession.objects.filter(user=self.request.user).prefetch_related('entries__transaction')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        POST /api/reconciliation/start/
        Body: { month: "2025-03", csv_content: "..." }
        Creates or reopens a session and runs the 3-pass matching.
        """
        month = request.data.get('month')
        csv_content = request.data.get('csv_content', '')

        if not month:
            return Response({'error': 'month is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Parse bank CSV
        bank_lines = _parse_bank_csv(csv_content)
        if not bank_lines:
            return Response({'error': 'Aucune ligne parsée. Vérifiez le format CSV (séparateur ; ou , avec colonnes Date/Libellé/Montant).'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create session
        session, _ = ReconciliationSession.objects.get_or_create(
            user=request.user, month=month,
            defaults={'status': 'open'},
        )
        if session.status == 'closed':
            return Response({'error': 'Ce mois est clôturé. Vous ne pouvez pas le re-réconcilier.'}, status=status.HTTP_400_BAD_REQUEST)

        # Clear previous entries
        session.entries.all().delete()

        # Get app transactions for the month
        app_txns = list(Transaction.objects.filter(
            user=request.user,
            date__startswith=month,
            type__in=['expense', 'saving'],
        ).order_by('date'))

        # Run matching
        results = match(app_txns, bank_lines)

        # Persist entries
        entries = []
        for r in results:
            entries.append(ReconciliationEntry(
                session=session,
                transaction=r['transaction'],
                bank_date=r['bank_date'],
                bank_label=r['bank_label'],
                bank_amount=r['bank_amount'],
                status=r['status'],
                match_score=r['match_score'],
            ))
        ReconciliationEntry.objects.bulk_create(entries)

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def match_manual(self, request, pk=None):
        """
        PATCH /api/reconciliation/{id}/match_manual/
        Body: { entry_id: X, transaction_id: Y }
        Manually link a bank entry to an app transaction.
        """
        session = self.get_object()
        if session.status == 'closed':
            return Response({'error': 'Session clôturée'}, status=status.HTTP_400_BAD_REQUEST)

        entry_id = request.data.get('entry_id')
        txn_id = request.data.get('transaction_id')

        try:
            entry = session.entries.get(pk=entry_id)
            txn = Transaction.objects.get(pk=txn_id, user=request.user)
        except (ReconciliationEntry.DoesNotExist, Transaction.DoesNotExist):
            return Response({'error': 'Entry ou transaction introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # Unlink previous match if exists
        session.entries.filter(transaction=txn).exclude(pk=entry.pk).update(
            transaction=None, status='unmatched_app', match_score=0
        )
        entry.transaction = txn
        entry.status = 'manual'
        entry.match_score = 1.0
        entry.save()

        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        POST /api/reconciliation/{id}/close/
        Clôture le mois — données figées.
        """
        session = self.get_object()
        if session.status == 'closed':
            return Response({'error': 'Déjà clôturé'}, status=status.HTTP_400_BAD_REQUEST)

        unmatched = session.entries.filter(status__in=['unmatched_app', 'unmatched_bank']).count()
        if unmatched > 0:
            return Response({
                'error': f'{unmatched} entrée(s) non réconciliée(s). Réconciliez ou ignorez avant de clôturer.',
                'unmatched': unmatched,
            }, status=status.HTTP_400_BAD_REQUEST)

        session.status = 'closed'
        session.closed_at = timezone.now()
        session.save()

        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def ignore_entry(self, request, pk=None):
        """Mark an unmatched entry as manually ignored (no counterpart)."""
        session = self.get_object()
        entry_id = request.data.get('entry_id')
        try:
            entry = session.entries.get(pk=entry_id)
        except ReconciliationEntry.DoesNotExist:
            return Response({'error': 'Entry introuvable'}, status=status.HTTP_404_NOT_FOUND)
        entry.status = 'manual'
        entry.match_score = 0.5
        entry.save()
        serializer = self.get_serializer(session)
        return Response(serializer.data)
