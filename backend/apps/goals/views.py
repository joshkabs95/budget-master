from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal

from .models import Goal
from .serializers import GoalSerializer
from .services.cashflow import project_cashflow


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user).select_related('savings_account')
        goal_type = self.request.query_params.get('type')
        horizon = self.request.query_params.get('horizon')
        if goal_type:
            qs = qs.filter(type=goal_type)
        if horizon:
            # Filter by horizon in Python (computed property)
            qs = [g for g in qs if g.horizon == horizon]
        return qs

    @action(detail=True, methods=['post'])
    def contribute(self, request, pk=None):
        goal = self.get_object()
        amount = Decimal(str(request.data.get('amount', 0)))
        if amount <= 0:
            return Response({"error": "Le montant doit être positif."}, status=status.HTTP_400_BAD_REQUEST)
        goal.current_amount += amount
        goal.save()
        return Response(GoalSerializer(goal, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def cashflow(self, request):
        months = int(request.query_params.get('months', 24))
        data = project_cashflow(request.user, months)
        return Response(data)
