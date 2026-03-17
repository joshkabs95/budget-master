from django.urls import path
from .views import GoalListCreateView, GoalDetailView, GoalContributeView, GoalCashFlowView

urlpatterns = [
    path('', GoalListCreateView.as_view(), name='goal-list'),
    path('<int:pk>/', GoalDetailView.as_view(), name='goal-detail'),
    path('<int:pk>/contribute/', GoalContributeView.as_view(), name='goal-contribute'),
    path('cashflow/', GoalCashFlowView.as_view(), name='goal-cashflow'),
]
