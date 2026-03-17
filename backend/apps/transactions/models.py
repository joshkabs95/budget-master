from django.db import models
from django.conf import settings

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('income', 'Revenu'),
        ('expense', 'Dépense'),
        ('saving', 'Épargne'),
    ]
    SOURCE_CHOICES = [
        ('manual', 'Manuel'),
        ('import', 'Import'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey('categories.Category', on_delete=models.SET_NULL, null=True, blank=True)
    savings_account = models.ForeignKey('savings.SavingsAccount', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    label = models.CharField(max_length=255)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    import_hash = models.CharField(max_length=64, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.label} — {self.amount}€ ({self.date})"
