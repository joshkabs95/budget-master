from django.db import models
from django.conf import settings


class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('checking', 'Compte courant'),
        ('joint', 'Compte joint'),
        ('pro', 'Compte professionnel'),
        ('other', 'Autre'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
    )
    name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='checking')
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    color = models.CharField(max_length=7, default='#00D4AA')
    icon = models.CharField(max_length=10, default='🏦')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user})"
