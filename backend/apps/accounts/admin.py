from django.contrib import admin
from .models import BankAccount

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'bank_name', 'account_type', 'initial_balance', 'is_default', 'user']
    list_filter = ['account_type', 'is_default']
