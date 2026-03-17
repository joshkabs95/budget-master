from django.db import models
from django.conf import settings


class Document(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('imported', 'Importé'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_type = models.CharField(max_length=5, choices=FILE_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    imported_at = models.DateTimeField(null=True, blank=True)
    transaction_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_type.upper()} - {self.created_at.strftime('%d/%m/%Y')}"
