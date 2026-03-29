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
    bank_account = models.ForeignKey('accounts.BankAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    goal = models.ForeignKey('goals.Goal', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    label = models.CharField(max_length=255)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    RECURRENCE_CHOICES = [
        ('monthly', 'Mensuel'),
        ('weekly', 'Hebdomadaire'),
        ('yearly', 'Annuel'),
    ]

    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    import_hash = models.CharField(max_length=64, blank=True, null=True)
    notes = models.TextField(blank=True, default='')
    is_recurring = models.BooleanField(default=False)
    recurrence = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date'], name='idx_txn_user_date'),
            models.Index(fields=['user', 'type'], name='idx_txn_user_type'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'import_hash'],
                condition=models.Q(import_hash__isnull=False),
                name='uniq_user_import_hash',
            )
        ]

    def __str__(self):
        return f"{self.label} — {self.amount}€ ({self.date})"
