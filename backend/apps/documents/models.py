from django.db import models
from django.conf import settings

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('imported', 'Importé'),
        ('error', 'Erreur'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=5)  # 'pdf' | 'csv'
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    imported_at = models.DateTimeField(null=True, blank=True)
    transaction_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
