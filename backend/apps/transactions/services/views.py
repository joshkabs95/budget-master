import csv
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from datetime import date
from decimal import Decimal

from .models import Transaction
from .serializers import TransactionSerializer
from .services.insights import generate_insights
from .services.recurring import detect_recurring
from apps.categories.models import Category


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related('category', 'savings_account').order_by('-date', '-id')
        month = self.request.query_params.get('month')
        category = self.request.query_params.get('category')
        txn_type = self.request.query_params.get('type')

        if month:
            try:
                year, m = month.split('-')
                qs = qs.filter(date__year=int(year), date__month=int(m))
            except ValueError:
                pass
        if category:
            qs = qs.filter(category_id=category)
        if txn_type:
            qs = qs.filter(type=txn_type)
        return qs

    def perform_create(self, serializer):
        txn = serializer.save(user=self.request.user)
        if txn.type == 'saving' and txn.savings_account:
            # Update savings account balance
            txn.savings_account.balance += txn.amount
            txn.savings_account.save()

    def perform_destroy(self, instance):
        if instance.type == 'saving' and instance.savings_account:
            instance.savings_account.balance -= instance.amount
            instance.savings_account.save()
        instance.delete()

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        month = request.query_params.get('month')

        if not month:
            today = date.today()
            month = f"{today.year}-{today.month:02d}"

        year, m = month.split('-')
        monthly = qs.filter(date__year=int(year), date__month=int(m))

        income = monthly.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        expenses = monthly.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        savings = monthly.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

        by_category = (
            monthly.filter(type='expense')
            .values('category__id', 'category__name', 'category__icon', 'category__color', 'category__rule_bucket', 'category__budget_limit')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        by_bucket = {}
        for row in by_category:
            bucket = row['category__rule_bucket'] or 'wants'
            by_bucket[bucket] = by_bucket.get(bucket, Decimal('0')) + (row['total'] or Decimal('0'))

        needs_pct = float(by_bucket.get('needs', 0) / income * 100) if income > 0 else 0
        wants_pct = float(by_bucket.get('wants', 0) / income * 100) if income > 0 else 0
        savings_pct = float(savings / income * 100) if income > 0 else 0

        # 6-month trend
        trend = (
            Transaction.objects.filter(user=request.user)
            .annotate(month=TruncMonth('date'))
            .values('month', 'type')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        # Risk score
        risk = _compute_risk(request.user, income, expenses, savings)

        return Response({
            "month": month,
            "income": float(income),
            "expenses": float(expenses),
            "savings": float(savings),
            "balance": float(income - expenses - savings),
            "savings_rate": round(savings_pct, 1),
            "rule_503020": {
                "needs": round(needs_pct, 1),
                "wants": round(wants_pct, 1),
                "savings": round(savings_pct, 1),
            },
            "by_category": list(by_category),
            "trend": list(trend),
            "risk": risk,
        })

    @action(detail=False, methods=['get'])
    def insights(self, request):
        data = generate_insights(request.user)
        return Response(data)

    @action(detail=False, methods=['get'])
    def recurring_detected(self, request):
        data = detect_recurring(request.user)
        return Response(data)

    @action(detail=False, methods=['get'])
    def export(self, request):  # noqa: E303
        qs = self.get_queryset()
        month = request.query_params.get('month', '')

        filename = f"transactions_{month or 'all'}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')  # BOM for Excel UTF-8

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Date', 'Libellé', 'Montant', 'Type', 'Catégorie', 'Récurrent', 'Fréquence', 'Notes'])
        type_labels = {'income': 'Revenu', 'expense': 'Dépense', 'saving': 'Épargne'}
        for t in qs:
            writer.writerow([
                t.date.strftime('%d/%m/%Y'),
                t.label,
                str(t.amount).replace('.', ','),
                type_labels.get(t.type, t.type),
                t.category.name if t.category else '',
                'Oui' if t.is_recurring else 'Non',
                dict(Transaction.RECURRENCE_CHOICES).get(t.recurrence, ''),
                t.notes,
            ])
        return response


def _compute_risk(user, income, expenses, savings) -> str:
    """low / medium / high basé sur la projection du mois suivant."""
    try:
        from apps.forecasting.engine import ForecastEngine
        proj = ForecastEngine(user).project(1)
        if proj:
            net = proj[0]['net']
            proj_income = proj[0]['projected_income']
            proj_expenses = proj[0]['projected_expenses']
            if net > 0 and proj_expenses < proj_income * 0.85:
                return 'low'
            elif net > -300:
                return 'medium'
            else:
                return 'high'
    except Exception:
        pass
    # Fallback: based on current month
    if income > 0:
        spend_ratio = float((expenses + savings) / income)
        if spend_ratio < 0.85:
            return 'low'
        elif spend_ratio < 1.0:
            return 'medium'
    return 'high'
