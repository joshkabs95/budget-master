from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryRuleViewSet

router = DefaultRouter()
router.register(r'', CategoryRuleViewSet, basename='category-rule')

urlpatterns = [
    path('', include(router.urls)),
]
