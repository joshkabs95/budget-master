from django.db import models
from django.conf import settings

class Category(models.Model):
    RULE_BUCKET_CHOICES = [
        ('needs', 'Besoins'),
        ('wants', 'Envies'),
        ('savings', 'Épargne'),
    ]
    TYPE_CHOICES = [
        ('income', 'Revenu'),
        ('expense', 'Dépense'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📦')
    color = models.CharField(max_length=7, default='#6b6b7e')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='expense')
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rule_bucket = models.CharField(max_length=10, choices=RULE_BUCKET_CHOICES, default='wants')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"
