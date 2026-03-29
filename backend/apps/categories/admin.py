from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'user', 'type', 'budget_limit', 'rule_bucket')
    list_filter = ('type', 'rule_bucket')
    search_fields = ('name', 'user__username')
    ordering = ('type', 'name')
    list_per_page = 40
