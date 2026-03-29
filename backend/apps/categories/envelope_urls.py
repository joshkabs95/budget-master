from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryBudgetViewSet

router = DefaultRouter()
router.register(r'', CategoryBudgetViewSet, basename='envelope')

urlpatterns = [path('', include(router.urls))]
