from django.contrib import admin
from .models import SavingsAccount, SavingsRule

admin.site.register(SavingsAccount)
admin.site.register(SavingsRule)
