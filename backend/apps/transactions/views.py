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
        qs = Transaction.objects.filter(user=self.request.user).select_related('category', 'savings_account', 'bank_account', 'goal').order_by('-date', '-id')
        month = self.request.query_params.get('month')
        category = self.request.query_params.get('category')
        txn_type = self.request.query_params.get('type')
        bank_account = self.request.query_params.get('bank_account')

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
        if bank_account:
            if bank_account == 'none':
                qs = qs.filter(bank_account__isnull=True)
            else:
                qs = qs.filter(bank_account_id=bank_account)
        if self.request.query_params.get('is_recurring') == 'true':
            qs = qs.filter(is_recurring=True)
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(label__icontains=search) | Q(notes__icontains=search))
        return qs

    def perform_create(self, serializer):
        txn = serializer.save(user=self.request.user)
        if txn.type == 'saving' and txn.savings_account:
            # Update savings account balance
            txn.savings_account.balance += txn.amount
            txn.savings_account.save()

    def perform_update(self, serializer):
        old_goal_id = serializer.instance.goal_id
        txn = serializer.save()
        new_goal_id = txn.goal_id
        if old_goal_id != new_goal_id:
            from apps.goals.models import Goal
            if old_goal_id:
                g = Goal.objects.filter(pk=old_goal_id).first()
                if g:
                    g.current_amount = max(g.current_amount - txn.amount, 0)
                    g.save(update_fields=['current_amount'])
            if new_goal_id:
                g = Goal.objects.filter(pk=new_goal_id).first()
                if g:
                    g.current_amount += txn.amount
                    g.save(update_fields=['current_amount'])

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
    def score_history(self, request):
        """Retourne le score financier mensuel sur les 6 derniers mois."""
        from datetime import date as _date
        today = _date.today()
        result = []
        for i in range(5, -1, -1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12; y -= 1
            month_str = f'{y}-{m:02d}'
            qs = Transaction.objects.filter(user=request.user, date__year=y, date__month=m)
            income   = float(qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
            expenses = float(qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
            savings  = float(qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)

            if income > 0:
                sav_rate = savings / income * 100
                # 50/30/20 buckets
                by_bucket = {}
                for row in (qs.filter(type='expense')
                              .values('category__rule_bucket')
                              .annotate(t=Sum('amount'))):
                    b = row['category__rule_bucket'] or 'wants'
                    by_bucket[b] = float(row['t'] or 0)
                needs_pct = by_bucket.get('needs', 0) / income * 100
                wants_pct = by_bucket.get('wants', 0) / income * 100
                budget_score = max(0, 100 - abs(needs_pct - 50) * 1.5 - abs(wants_pct - 30) * 1.5)
                sav_score    = min(100, (sav_rate / 20) * 100)
                score = round(budget_score * 0.5 + sav_score * 0.5)
            else:
                score = 0
                sav_rate = 0.0
                expenses = 0.0

            result.append({
                'month': month_str,
                'score': score,
                'savings_rate': round(sav_rate, 1),
                'income': round(income, 2),
                'expenses': round(expenses, 2),
            })
        return Response(result)

    @action(detail=False, methods=['get'])
    def weekday_stats(self, request):
        """Dépenses moyennes par jour de la semaine (3 derniers mois)."""
        from datetime import date as _date, timedelta
        months = int(request.query_params.get('months', 3))
        today = _date.today()
        # Start of N months ago
        start = today.replace(day=1)
        for _ in range(months - 1):
            start = (start - timedelta(days=1)).replace(day=1)

        qs = Transaction.objects.filter(
            user=request.user,
            type='expense',
            date__gte=start,
        )
        totals = [0.0] * 7
        counts = [0] * 7
        for t in qs:
            wd = t.date.weekday()
            totals[wd] += float(t.amount)
            counts[wd] += 1

        days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        return Response([
            {
                'day': days[i],
                'total': round(totals[i], 2),
                'count': counts[i],
                'avg': round(totals[i] / counts[i], 2) if counts[i] > 0 else 0,
            }
            for i in range(7)
        ])

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
