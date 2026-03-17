from django.db import models
from django.conf import settings


class SavingsAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_accounts')
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=7, default='#3b82f6')
    icon = models.CharField(max_length=10, default='💰')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'savings_accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.icon} {self.name}"

    def recalculate_balance(self):
        from apps.transactions.models import Transaction
        from django.db.models import Sum
        total = Transaction.objects.filter(
            user=self.user,
            savings_account=self,
            type='saving'
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.balance = total
        self.save(update_fields=['balance'])


class SavingsRule(models.Model):
    MODE_CHOICES = [('strict', 'Strict'), ('adaptive', 'Adaptatif')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_rule')
    savings_target = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    needs_target = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    wants_target = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    savings_tolerance = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    needs_tolerance = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    wants_tolerance = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    savings_floor = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    needs_floor = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    wants_floor = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    compensation_order = models.JSONField(default=list)
    window_months = models.IntegerField(default=3)
    catchup_max_months = models.IntegerField(default=3)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='adaptive')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'savings_rules'

    def __str__(self):
        return f"Règle épargne de {self.user.email}"
