from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum
from decimal import Decimal

from .models import BankAccount
from .serializers import BankAccountSerializer
from apps.transactions.models import Transaction


class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Monthly balance history for the account."""
        account = self.get_object()
        qs = Transaction.objects.filter(bank_account=account).order_by('date')

        monthly = {}
        for t in qs:
            key = t.date.strftime('%Y-%m')
            if key not in monthly:
                monthly[key] = {'income': 0, 'expenses': 0, 'savings': 0}
            v = float(t.amount)
            if t.type == 'income':
                monthly[key]['income'] += v
            elif t.type == 'expense':
                monthly[key]['expenses'] += v
            elif t.type == 'saving':
                monthly[key]['savings'] += v

        running = float(account.initial_balance)
        result = []
        for month in sorted(monthly.keys()):
            d = monthly[month]
            running += d['income'] - d['expenses'] - d['savings']
            result.append({
                'month': month,
                'income': d['income'],
                'expenses': d['expenses'],
                'savings': d['savings'],
                'balance': round(running, 2),
            })

        return Response(result)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Total balance across all accounts."""
        accounts = self.get_queryset()
        total = Decimal('0')
        for acc in accounts:
            qs = Transaction.objects.filter(bank_account=acc)
            income   = qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
            expenses = qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
            savings  = qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')
            total += acc.initial_balance + income - expenses - savings
        return Response({'total_balance': float(total), 'account_count': accounts.count()})
