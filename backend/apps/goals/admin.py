from django.contrib import admin
from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'target_amount', 'current_amount', 'progress_bar', 'deadline')
    list_filter = ('deadline',)
    search_fields = ('name', 'user__username')
    ordering = ('deadline',)
    list_per_page = 25

    @admin.display(description='Progression')
    def progress_bar(self, obj):
        from django.utils.html import format_html
        if not obj.target_amount:
            return '—'
        pct = min(int(obj.current_amount / obj.target_amount * 100), 100)
        color = '#4ade80' if pct >= 80 else '#fb923c' if pct >= 40 else '#f87171'
        return format_html(
            '<div style="background:#2a2a2a;border-radius:4px;width:120px;height:10px;">'
            '<div style="background:{};width:{}%;height:100%;border-radius:4px;"></div>'
            '</div> {}%',
            color, pct, pct
        )
