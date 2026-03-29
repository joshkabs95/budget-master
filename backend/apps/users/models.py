from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    locale = models.CharField(max_length=10, default='fr-FR')
    currency = models.CharField(max_length=3, default='EUR')
    onboarding_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'
