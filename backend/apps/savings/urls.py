from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SavingsAccountViewSet, SavingsRuleView, SavingsSummaryView, CompensationView

router = DefaultRouter()
router.register(r'accounts', SavingsAccountViewSet, basename='savings-account')

urlpatterns = [
    path('', include(router.urls)),
    path('rule/', SavingsRuleView.as_view(), name='savings-rule'),
    path('summary/', SavingsSummaryView.as_view(), name='savings-summary'),
    path('compensation/', CompensationView.as_view(), name='savings-compensation'),
]
