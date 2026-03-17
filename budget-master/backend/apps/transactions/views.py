from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from datetime import date, timedelta
import calendar
from .models import Transaction
from .serializers import TransactionSerializer
from .services.insights import generate_insights


class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related('category', 'savings_account')

        month = self.request.query_params.get('month')
        if month:
            try:
                year, m = month.split('-')
                qs = qs.filter(date__year=year, date__month=m)
            except (ValueError, AttributeError):
                pass

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)

        t_type = self.request.query_params.get('type')
        if t_type:
            qs = qs.filter(type=t_type)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionStatsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        month = request.query_params.get('month')
        now = timezone.now().date()

        if month:
            try:
                year, m = month.split('-')
                year, m = int(year), int(m)
            except (ValueError, AttributeError):
                year, m = now.year, now.month
        else:
            year, m = now.year, now.month

        month_start = date(year, m, 1)
        month_end = date(year, m, calendar.monthrange(year, m)[1])

        qs = Transaction.objects.filter(
            user=request.user,
            date__gte=month_start,
            date__lte=month_end
        )

        income = float(qs.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0)
        expenses = float(qs.filter(type='expense').aggregate(t=Sum('amount'))['t'] or 0)
        savings = float(qs.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0)
        balance = income - expenses - savings
        savings_rate = round((savings / income * 100), 1) if income > 0 else 0

        # Category breakdown
        from apps.categories.models import Category
        cats = Category.objects.filter(user=request.user, type='expense')
        category_breakdown = []
        for cat in cats:
            spent = float(qs.filter(category=cat, type='expense').aggregate(t=Sum('amount'))['t'] or 0)
            if spent > 0:
                category_breakdown.append({
                    'id': cat.id,
                    'category': cat.name,
                    'name': cat.name,
                    'icon': cat.icon,
                    'color': cat.color,
                    'amount': spent,
                    'percentage': round((spent / expenses * 100), 1) if expenses > 0 else 0,
                    'budget_limit': float(cat.budget_limit) if cat.budget_limit else None,
                    'rule_bucket': cat.rule_bucket,
                })

        category_breakdown.sort(key=lambda x: x['amount'], reverse=True)

        # Monthly trend (last 6 months)
        trend = []
        for i in range(5, -1, -1):
            d = now.replace(day=1)
            for _ in range(i):
                d = (d - timedelta(days=1)).replace(day=1)
            last_day = calendar.monthrange(d.year, d.month)[1]
            m_end = d.replace(day=last_day)
            m_qs = Transaction.objects.filter(user=request.user, date__gte=d, date__lte=m_end)
            trend.append({
                'month': d.strftime('%Y-%m'),
                'label': d.strftime('%b %Y'),
                'income': float(m_qs.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0),
                'expenses': float(m_qs.filter(type='expense').aggregate(t=Sum('amount'))['t'] or 0),
                'savings': float(m_qs.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0),
            })

        return Response({
            'total_income': income,
            'total_expenses': expenses,
            'total_savings': savings,
            'balance': balance,
            'savings_rate': savings_rate,
            'by_category': category_breakdown,
            'trend': trend,
        })


class TransactionInsightsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        insights = generate_insights(request.user)
        score = _calculate_score(request.user)
        return Response({'insights': insights, 'score': score})


def _calculate_score(user):
    from apps.categories.models import Category
    from apps.goals.models import Goal
    now = timezone.now().date()
    month_start = now.replace(day=1)

    qs = Transaction.objects.filter(user=user, date__gte=month_start)
    income = float(qs.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0)
    savings = float(qs.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0)

    # Budget respect (40%)
    budget_score = 40
    cats = Category.objects.filter(user=user, type='expense', budget_limit__isnull=False)
    if cats.exists():
        over_count = 0
        for cat in cats:
            spent = float(qs.filter(category=cat, type='expense').aggregate(t=Sum('amount'))['t'] or 0)
            if cat.budget_limit and spent > float(cat.budget_limit):
                over_count += 1
        budget_score = max(0, 40 - (over_count * 10))

    # Savings respect (40%)
    savings_score = 0
    if income > 0:
        savings_rate = (savings / income) * 100
        if savings_rate >= 20:
            savings_score = 40
        elif savings_rate >= 15:
            savings_score = 30
        elif savings_rate >= 10:
            savings_score = 20
        else:
            savings_score = 10

    # Goals progress (20%)
    goals = Goal.objects.filter(user=user)
    goals_score = 0
    if goals.exists():
        total_progress = sum(
            min(1.0, float(g.current_amount) / float(g.target_amount)) if g.target_amount > 0 else 0
            for g in goals
        )
        goals_score = int((total_progress / goals.count()) * 20)

    return min(100, budget_score + savings_score + goals_score)
