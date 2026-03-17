from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/savings/', include('apps.savings.urls')),
    path('api/goals/', include('apps.goals.urls')),
    path('api/documents/', include('apps.documents.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
