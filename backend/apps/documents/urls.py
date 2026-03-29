from django.urls import path
from .views import DocumentUploadView, DocumentPreviewView, DocumentImportView, MonthlyReportPDFView, TemplateDownloadView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:pk>/preview/', DocumentPreviewView.as_view(), name='document-preview'),
    path('<int:pk>/import/', DocumentImportView.as_view(), name='document-import'),
    path('report/pdf/', MonthlyReportPDFView.as_view(), name='monthly-report-pdf'),
    path('template/', TemplateDownloadView.as_view(), name='document-template'),
]
