from django.contrib import admin
from .models import ReconciliationSession, ReconciliationEntry


class ReconciliationEntryInline(admin.TabularInline):
    model = ReconciliationEntry
    extra = 0
    readonly_fields = ['bank_date', 'bank_label', 'bank_amount', 'status', 'match_score']


@admin.register(ReconciliationSession)
class ReconciliationSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'status', 'created_at', 'closed_at']
    list_filter = ['status']
    inlines = [ReconciliationEntryInline]
