from django.db import models
from django.conf import settings


class ReconciliationSession(models.Model):
    STATUS_CHOICES = [('open', 'Ouverte'), ('closed', 'Clôturée')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    month = models.CharField(max_length=7)  # YYYY-MM
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reconciliation_sessions'
        unique_together = ['user', 'month']
        ordering = ['-month']

    def __str__(self):
        return f"{self.user} — {self.month} ({self.status})"


class ReconciliationEntry(models.Model):
    STATUS_CHOICES = [
        ('auto', 'Correspondance automatique'),
        ('manual', 'Correspondance manuelle'),
        ('unmatched_app', 'Non trouvé en banque'),
        ('unmatched_bank', 'Non trouvé dans l\'app'),
    ]

    session = models.ForeignKey(ReconciliationSession, on_delete=models.CASCADE, related_name='entries')
    # App side
    transaction = models.ForeignKey(
        'transactions.Transaction', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reconciliation_entries'
    )
    # Bank side
    bank_date = models.DateField(null=True, blank=True)
    bank_label = models.CharField(max_length=255, blank=True)
    bank_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Match
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unmatched_bank')
    match_score = models.FloatField(default=0)

    class Meta:
        db_table = 'reconciliation_entries'
        ordering = ['bank_date', 'bank_amount']
