from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import SavingsAccount, SavingsRule
from .serializers import SavingsAccountSerializer, SavingsRuleSerializer
from .services.adaptive_rule import AdaptiveRuleEngine
from .services.savings_summary import get_monthly_savings_summary, get_heatmap_data


class SavingsAccountListCreateView(generics.ListCreateAPIView):
    serializer_class = SavingsAccountSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return SavingsAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavingsAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SavingsAccountSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return SavingsAccount.objects.filter(user=self.request.user)


class SavingsRuleView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            rule = request.user.savings_rule
            return Response(SavingsRuleSerializer(rule).data)
        except SavingsRule.DoesNotExist:
            return Response({'detail': 'Aucune règle configurée.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            rule = request.user.savings_rule
            serializer = SavingsRuleSerializer(rule, data=request.data, partial=True)
        except SavingsRule.DoesNotExist:
            serializer = SavingsRuleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data)


class SavingsSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        accounts = SavingsAccount.objects.filter(user=request.user)
        total_balance = sum(float(a.balance) for a in accounts)
        total_target = sum(float(a.target) for a in accounts if a.target)

        engine = AdaptiveRuleEngine()
        try:
            rule = request.user.savings_rule
            window = rule.window_months
        except SavingsRule.DoesNotExist:
            window = 3
            rule = None

        current_rates = engine.get_current_rates(request.user, window)
        monthly_summary = get_monthly_savings_summary(request.user, 12)
        heatmap = get_heatmap_data(request.user, 12)

        return Response({
            'total_balance': total_balance,
            'total_target': total_target,
            'accounts_count': accounts.count(),
            'current_rates': current_rates,
            'monthly_summary': monthly_summary,
            'heatmap': heatmap,
        })


class CompensationView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            rule = request.user.savings_rule
        except SavingsRule.DoesNotExist:
            return Response({'status': 'no_rule', 'plan': None})

        engine = AdaptiveRuleEngine()
        current_rates = engine.get_current_rates(request.user, rule.window_months)
        result = engine.compensate(rule, current_rates)
        result['current_rates'] = current_rates
        result['rule'] = SavingsRuleSerializer(rule).data
        return Response(result)
