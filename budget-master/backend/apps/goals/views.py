from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import date, timedelta
from .models import Goal
from .serializers import GoalSerializer
from .services.cashflow import project_cashflow


class GoalListCreateView(generics.ListCreateAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user)
        g_type = self.request.query_params.get('type')
        if g_type:
            qs = qs.filter(type=g_type)
        horizon = self.request.query_params.get('horizon')
        if horizon:
            today = date.today()
            if horizon == 'short':
                qs = qs.filter(deadline__lte=today + timedelta(days=89))
            elif horizon == 'medium':
                qs = qs.filter(
                    deadline__gt=today + timedelta(days=89),
                    deadline__lte=today + timedelta(days=364)
                )
            elif horizon == 'long':
                qs = qs.filter(deadline__gt=today + timedelta(days=364))
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalContributeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            goal = Goal.objects.get(pk=pk, user=request.user)
        except Goal.DoesNotExist:
            return Response({'detail': 'Objectif non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get('amount')
        if not amount:
            return Response({'detail': 'Montant requis.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return Response({'detail': 'Montant invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        goal.current_amount = float(goal.current_amount) + amount
        goal.save()
        return Response(GoalSerializer(goal).data)


class GoalCashFlowView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cashflow = project_cashflow(request.user, 24)
        return Response({'cashflow': cashflow})
