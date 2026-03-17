from django.urls import path
from .views import (
    SavingsAccountListCreateView,
    SavingsAccountDetailView,
    SavingsRuleView,
    SavingsSummaryView,
    CompensationView,
)

urlpatterns = [
    path('accounts/', SavingsAccountListCreateView.as_view(), name='savings-account-list'),
    path('accounts/<int:pk>/', SavingsAccountDetailView.as_view(), name='savings-account-detail'),
    path('rule/', SavingsRuleView.as_view(), name='savings-rule'),
    path('summary/', SavingsSummaryView.as_view(), name='savings-summary'),
    path('compensation/', CompensationView.as_view(), name='savings-compensation'),
]
