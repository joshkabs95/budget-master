from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'user', 'file_type', 'status', 'transaction_count', 'created_at', 'imported_at')
    list_filter = ('status', 'file_type', 'created_at')
    search_fields = ('file', 'user__username')
    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'
