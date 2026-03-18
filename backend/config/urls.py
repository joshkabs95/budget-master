from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import FileResponse, Http404, JsonResponse
import os

def serve_react(request, path=''):
    index = settings.FRONTEND_DIR / 'index.html'
    if index.exists():
        return FileResponse(open(index, 'rb'), content_type='text/html')
    raise Http404("Frontend not built. Run: cd frontend && npm run build")

def serve_static_asset(request, path):
    file_path = settings.FRONTEND_DIR / path
    if file_path.exists() and file_path.is_file():
        import mimetypes
        mime, _ = mimetypes.guess_type(str(file_path))
        return FileResponse(open(file_path, 'rb'), content_type=mime or 'application/octet-stream')
    raise Http404()

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('api/health/', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/savings/', include('apps.savings.urls')),
    path('api/goals/', include('apps.goals.urls')),
    path('api/documents/', include('apps.documents.urls')),
    path('api/forecast/', include('apps.forecasting.urls')),
    # Serve frontend static assets
    re_path(r'^assets/(?P<path>.+)$', serve_static_asset),
    # Catch-all → React index.html (client-side routing)
    re_path(r'^(?!api/).*$', serve_react),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
