from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, CategoryBudgetViewSet, CategoryRuleViewSet

router = DefaultRouter()
router.register(r'', CategoryViewSet, basename='category')

envelope_router = DefaultRouter()
envelope_router.register(r'', CategoryBudgetViewSet, basename='envelope')

rules_router = DefaultRouter()
rules_router.register(r'', CategoryRuleViewSet, basename='category-rule')

urlpatterns = [
    path('', include(router.urls)),
]
