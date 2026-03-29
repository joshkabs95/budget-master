from rest_framework.routers import DefaultRouter
from .views import ReconciliationViewSet

router = DefaultRouter()
router.register(r'', ReconciliationViewSet, basename='reconciliation')

urlpatterns = router.urls
