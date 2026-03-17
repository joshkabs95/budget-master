from django.urls import path
from .views import (
    TransactionListCreateView,
    TransactionDetailView,
    TransactionStatsView,
    TransactionInsightsView,
)

urlpatterns = [
    path('', TransactionListCreateView.as_view(), name='transaction-list'),
    path('<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('stats/', TransactionStatsView.as_view(), name='transaction-stats'),
    path('insights/', TransactionInsightsView.as_view(), name='transaction-insights'),
]
