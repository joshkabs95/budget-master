from django.contrib import admin
from .models import SavingsAccount, SavingsRule


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'user', 'balance', 'target', 'interest_rate')
    search_fields = ('name', 'user__username')
    ordering = ('-balance',)
    list_per_page = 25


@admin.register(SavingsRule)
class SavingsRuleAdmin(admin.ModelAdmin):
    list_display = ('user', 'mode', 'active', 'savings_target', 'needs_target', 'wants_target')
    list_filter = ('mode', 'active')
    search_fields = ('user__username',)
    list_per_page = 25
