from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'label', 'category', 'amount_colored', 'type', 'is_recurring', 'recurrence')
    list_filter = ('type', 'is_recurring', 'recurrence', 'category', 'date')
    search_fields = ('label', 'user__username', 'user__email', 'notes')
    date_hierarchy = 'date'
    ordering = ('-date',)
    list_per_page = 30

    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'date', 'label', 'amount', 'type', 'category')
        }),
        ('Récurrence', {
            'fields': ('is_recurring', 'recurrence'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Montant')
    def amount_colored(self, obj):
        from django.utils.html import format_html
        color = '#4ade80' if obj.type == 'income' else '#f87171'
        sign = '+' if obj.type == 'income' else '-'
        return format_html(
            '<span style="color:{}; font-weight:600;">{}{} €</span>',
            color, sign, obj.amount
        )
