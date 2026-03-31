from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from django.utils import timezone
from datetime import date as _date

from .models import Document
from .serializers import DocumentSerializer
from .services.parser import parse_file
from apps.transactions.models import Transaction
from apps.transactions.services.categorization import compute_import_hash


class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class DocumentPreviewView(APIView):
    def get(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document non trouvé."}, status=404)

        categories, goals, scores = [], [], {}

        if doc.file_type == 'xlsx':
            from .services.excel_parser import parse_excel
            result = parse_excel(doc.file.path)
            transactions = result.get('transactions', [])
            categories   = result.get('categories', [])
            goals        = result.get('goals', [])
            scores       = result.get('scores', {})
        else:
            transactions = parse_file(doc.file.path, doc.file_type)

        for t in transactions:
            t['is_duplicate'] = Transaction.objects.filter(import_hash=t['import_hash']).exists()

        return Response({
            "document_id": doc.id,
            "file_type": doc.file_type,
            "transactions": transactions,
            "total": len(transactions),
            "duplicates": sum(1 for t in transactions if t['is_duplicate']),
            "categories": categories,
            "goals": goals,
            "scores": scores,
        })


class DocumentImportView(APIView):
    def post(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document non trouvé."}, status=404)

        selected = request.data.get('transactions', [])
        imported = 0
        skipped = 0

        for txn_data in selected:
            import_hash = txn_data.get('import_hash')
            if Transaction.objects.filter(import_hash=import_hash).exists():
                skipped += 1
                continue

            from apps.categories.models import Category
            category = None
            cat_name = txn_data.get('category') or txn_data.get('suggested_category', 'Autre')
            cat_obj = Category.objects.filter(user=request.user, name=cat_name).first()

            Transaction.objects.create(
                user=request.user,
                category=cat_obj,
                amount=txn_data['amount'],
                label=txn_data['label'],
                date=txn_data['date'],
                type=txn_data.get('type', 'expense'),
                source='import',
                import_hash=import_hash,
            )
            imported += 1

        # ── Import categories / goals / scores from xlsx ──────────────────
        cats_created = goals_created = 0

        if doc.file_type == 'xlsx':
            from .services.excel_parser import parse_excel
            from apps.categories.models import Category
            from apps.goals.models import Goal
            from apps.savings.models import SavingsRule
            from datetime import datetime

            full = parse_excel(doc.file.path)

            for cat_data in full.get('categories', []):
                _, created = Category.objects.get_or_create(
                    user=request.user,
                    name=cat_data['name'],
                    defaults={
                        'icon':         cat_data.get('icon', '📁'),
                        'rule_bucket':  cat_data.get('bucket', 'wants'),
                        'color':        '#64748b',
                    }
                )
                if created:
                    cats_created += 1

            from apps.savings.models import SavingsAccount
            for goal_data in full.get('goals', []):
                deadline = goal_data.get('deadline') or None
                if deadline:
                    try:
                        datetime.strptime(deadline, '%Y-%m-%d')
                    except ValueError:
                        deadline = None

                # Résolution du compte épargne par nom
                savings_account = None
                acc_name = goal_data.get('savings_account')
                if acc_name:
                    savings_account = SavingsAccount.objects.filter(
                        user=request.user, name__iexact=acc_name
                    ).first()

                _, created = Goal.objects.get_or_create(
                    user=request.user,
                    name=goal_data['name'],
                    defaults={
                        'icon':            goal_data.get('icon', '🎯'),
                        'target_amount':   goal_data['target_amount'],
                        'current_amount':  goal_data.get('current_amount', 0),
                        'deadline':        deadline or '2025-12-31',
                        'type':            goal_data.get('type', 'savings'),
                        'color':           '#a855f7',
                        'savings_account': savings_account,
                    }
                )
                if created:
                    goals_created += 1

            scores = full.get('scores', {})
            if scores:
                rule = SavingsRule.objects.filter(user=request.user, active=True).first()
                if rule:
                    # Map category names to IDs
                    from apps.categories.models import Category as Cat
                    id_scores = {}
                    for cat_name, score in scores.items():
                        cat_obj = Cat.objects.filter(user=request.user, name=cat_name).first()
                        if cat_obj:
                            id_scores[str(cat_obj.id)] = score
                    if id_scores:
                        rule.wants_scores = {**(rule.wants_scores or {}), **id_scores}
                        rule.save(update_fields=['wants_scores'])

        doc.status = 'imported'
        doc.imported_at = timezone.now()
        doc.transaction_count = imported
        doc.save()

        return Response({
            "imported": imported,
            "skipped": skipped,
            "categories_created": cats_created,
            "goals_created": goals_created,
            "message": (
                f"{imported} transaction(s) importée(s)"
                + (f", {skipped} doublon(s) ignoré(s)" if skipped else "")
                + (f", {cats_created} catégorie(s) créée(s)" if cats_created else "")
                + (f", {goals_created} objectif(s) créé(s)" if goals_created else "")
                + "."
            ),
        })


class TemplateDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get('month')
        if not month:
            today = _date.today()
            month = f"{today.year}-{today.month:02d}"
        try:
            from .services.excel_template import generate_template
            from apps.savings.models import SavingsAccount
            acc_names = list(
                SavingsAccount.objects.filter(user=request.user)
                .values_list('name', flat=True)
            )
            xlsx_bytes = generate_template(month, savings_accounts=acc_names)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        filename = f"budget_master_seed_{month}.xlsx"
        response = HttpResponse(
            xlsx_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class MonthlyReportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get('month')
        if not month:
            from datetime import date
            today = date.today()
            month = f"{today.year}-{today.month:02d}"

        try:
            from .pdf_report import generate_monthly_report
            pdf_bytes = generate_monthly_report(request.user, month)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        filename = f"budget-master-{month}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
