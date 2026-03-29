from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'type', 'severity_badge', 'message_short', 'read', 'email_sent')
    list_filter = ('type', 'severity', 'read', 'email_sent', 'created_at')
    search_fields = ('user__username', 'message')
    ordering = ('-created_at',)
    list_per_page = 30
    date_hierarchy = 'created_at'
    actions = ['mark_all_read']

    @admin.display(description='Sévérité')
    def severity_badge(self, obj):
        from django.utils.html import format_html
        colors = {'green': '#4ade80', 'orange': '#fb923c', 'red': '#f87171'}
        color = colors.get(obj.severity, '#888')
        return format_html(
            '<span style="background:{};color:#000;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;">{}</span>',
            color, obj.severity
        )

    @admin.display(description='Message')
    def message_short(self, obj):
        return obj.message[:80] + '…' if len(obj.message) > 80 else obj.message

    @admin.action(description='Marquer comme lues')
    def mark_all_read(self, request, queryset):
        queryset.update(read=True)
