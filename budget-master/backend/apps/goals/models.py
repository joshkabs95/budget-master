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
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField()
    icon = models.CharField(max_length=10, default='🎯')
    color = models.CharField(max_length=7, default='#a855f7')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'goals'
        ordering = ['deadline']

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def horizon(self):
        delta = (self.deadline - date.today()).days
        if delta < 90:
            return 'short'
        if delta < 365:
            return 'medium'
        return 'long'

    @property
    def progress_pct(self):
        if float(self.target_amount) > 0:
            return round(float(self.current_amount) / float(self.target_amount) * 100, 1)
        return 0

    @property
    def days_remaining(self):
        return (self.deadline - date.today()).days
