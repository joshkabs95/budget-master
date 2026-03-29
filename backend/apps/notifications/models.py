from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('risk_high',        'Risque élevé'),
        ('budget_exceeded',  'Budget dépassé'),
        ('budget_warning',   'Budget en alerte'),
        ('anomaly',          'Anomalie détectée'),
        ('savings_gap',      'Écart épargne'),
        ('risk_score',       'Score de risque'),
        ('streak',           'Streak épargne'),
        ('info',             'Information'),
    ]
    SEVERITY_CHOICES = [('green', 'green'), ('orange', 'orange'), ('red', 'red')]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type        = models.CharField(max_length=30, choices=TYPE_CHOICES)
    severity    = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='orange')
    message     = models.TextField()
    read        = models.BooleanField(default=False)
    email_sent  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.type} — {self.user}"
