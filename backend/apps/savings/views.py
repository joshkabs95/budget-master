from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date

from .models import SavingsAccount, SavingsRule
from .serializers import SavingsAccountSerializer, SavingsRuleSerializer
from .services.adaptive_rule import AdaptiveRuleEngine
from .services.savings_summary import get_savings_summary


class SavingsAccountViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsAccountSerializer

    def get_queryset(self):
        return SavingsAccount.objects.filter(user=self.request.user)


class SavingsRuleView(generics.GenericAPIView):
    serializer_class = SavingsRuleSerializer

    def get(self, request):
        try:
            rule = SavingsRule.objects.get(user=request.user, active=True)
            return Response(SavingsRuleSerializer(rule).data)
        except SavingsRule.DoesNotExist:
            return Response(None, status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        SavingsRule.objects.filter(user=request.user).update(active=False)
        serializer = SavingsRuleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SavingsSummaryView(generics.GenericAPIView):
    def get(self, request):
        month = request.query_params.get('month')
        data = get_savings_summary(request.user, month)
        return Response(data)


class CompensationView(generics.GenericAPIView):
    def get(self, request):
        from apps.transactions.models import Transaction
        from django.db.models import Sum
        from decimal import Decimal

        try:
            rule = SavingsRule.objects.get(user=request.user, active=True)
        except SavingsRule.DoesNotExist:
            return Response({"error": "Aucune règle d'épargne active."}, status=404)

        month = request.query_params.get('month')
        today = date.today()

        if rule.mode == 'adaptive':
            # Use sliding window (default: 3 months)
            cutoff = today.replace(day=1)
            for _ in range(rule.window_months - 1):
                if cutoff.month == 1:
                    cutoff = cutoff.replace(year=cutoff.year - 1, month=12)
                else:
                    cutoff = cutoff.replace(month=cutoff.month - 1)
            txns = Transaction.objects.filter(user=request.user, date__gte=cutoff)
        else:
            if month:
                y, m = month.split('-')
                txns = Transaction.objects.filter(user=request.user, date__year=int(y), date__month=int(m))
            else:
                txns = Transaction.objects.filter(user=request.user, date__year=today.year, date__month=today.month)

        income = txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        savings = txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        needs = txns.filter(type='expense', category__rule_bucket='needs').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        wants = txns.filter(type='expense', category__rule_bucket='wants').aggregate(s=Sum('amount'))['s'] or Decimal('0')

        if income == 0:
            return Response({"error": "Aucun revenu enregistré pour cette période."})

        current_rates = {
            "savings": round(float(savings / income * 100), 1),
            "needs": round(float(needs / income * 100), 1),
            "wants": round(float(wants / income * 100), 1),
        }

        engine = AdaptiveRuleEngine()
        result = engine.compensate(rule, current_rates)
        return Response(result)
