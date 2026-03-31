from django.db import models
from django.conf import settings
from datetime import date

class Goal(models.Model):
    TYPE_CHOICES = [
        ('savings', 'Épargne'),
        ('expense', 'Dépense future'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    savings_account = models.ForeignKey('savings.SavingsAccount', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deadline = models.DateField()
    icon = models.CharField(max_length=10, default='🎯')
    color = models.CharField(max_length=7, default='#a855f7')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'goals'
        ordering = ['deadline']

    def __str__(self):
        return f"{self.icon} {self.name} — {self.current_amount}/{self.target_amount}€"

    @property
    def horizon(self):
        delta = (self.deadline - date.today()).days
        if delta < 90:
            return 'short'
        if delta < 365:
            return 'medium'
        return 'long'

    def get_effective_amount(self):
        """
        Si un compte épargne est lié, la progression = somme des transactions
        'saving' rattachées à cet objectif (source de vérité).
        Sinon, utilise current_amount saisi manuellement.
        """
        if self.savings_account_id:
            from apps.transactions.models import Transaction
            from django.db.models import Sum
            total = Transaction.objects.filter(
                goal=self, type='saving'
            ).aggregate(s=Sum('amount'))['s'] or 0
            return float(total)
        return float(self.current_amount)

    @property
    def progress(self):
        if self.target_amount > 0:
            return round(float(self.current_amount / self.target_amount * 100), 1)
        return 0.0

    @property
    def monthly_required(self):
        """Monthly contribution needed to reach goal by deadline."""
        today = date.today()
        delta_days = (self.deadline - today).days
        if delta_days <= 0:
            return 0.0
        months_left = max(1, delta_days / 30)
        remaining = float(self.target_amount - self.current_amount)
        return round(remaining / months_left, 2)
