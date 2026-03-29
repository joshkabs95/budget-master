from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


# ── Inlines ────────────────────────────────────────────────────────────────

class TransactionInline(admin.TabularInline):
    from apps.transactions.models import Transaction
    model = Transaction
    extra = 0
    fields = ('date', 'label', 'amount', 'type', 'category', 'is_recurring', 'notes')
    ordering = ('-date',)
    show_change_link = True
    verbose_name_plural = '💱 Transactions'


class CategoryInline(admin.TabularInline):
    from apps.categories.models import Category
    model = Category
    extra = 0
    fields = ('name', 'icon', 'type', 'budget_limit', 'rule_bucket')
    ordering = ('type', 'name')
    show_change_link = True
    verbose_name_plural = '🏷️ Catégories'


class SavingsAccountInline(admin.TabularInline):
    from apps.savings.models import SavingsAccount
    model = SavingsAccount
    extra = 0
    fields = ('name', 'icon', 'balance', 'target', 'interest_rate')
    ordering = ('-balance',)
    show_change_link = True
    verbose_name_plural = '🏦 Comptes épargne'


class SavingsRuleInline(admin.StackedInline):
    from apps.savings.models import SavingsRule
    model = SavingsRule
    extra = 0
    fields = (
        'mode', 'active',
        ('savings_target', 'needs_target', 'wants_target'),
        ('savings_tolerance', 'needs_tolerance', 'wants_tolerance'),
        ('savings_floor', 'needs_floor', 'wants_floor'),
        'window_months', 'catchup_max_months',
    )
    show_change_link = True
    verbose_name_plural = "⚙️ Règle d'épargne"


class GoalInline(admin.TabularInline):
    from apps.goals.models import Goal
    model = Goal
    extra = 0
    fields = ('name', 'icon', 'type', 'target_amount', 'current_amount', 'deadline', 'progress_pct')
    readonly_fields = ('progress_pct',)
    ordering = ('deadline',)
    show_change_link = True
    verbose_name_plural = '🎯 Objectifs'

    @admin.display(description='%')
    def progress_pct(self, obj):
        if not obj.target_amount:
            return '—'
        pct = min(int(obj.current_amount / obj.target_amount * 100), 100)
        color = '#4ade80' if pct >= 80 else '#fb923c' if pct >= 40 else '#f87171'
        return format_html(
            '<span style="color:{};font-weight:700;">{}%</span>', color, pct
        )


class NotificationInline(admin.TabularInline):
    from apps.notifications.models import Notification
    model = Notification
    extra = 0
    fields = ('created_at', 'type', 'severity', 'message', 'read', 'email_sent')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    show_change_link = True
    verbose_name_plural = '🔔 Notifications'


class DocumentInline(admin.TabularInline):
    from apps.documents.models import Document
    model = Document
    extra = 0
    fields = ('file', 'file_type', 'status', 'transaction_count', 'created_at', 'imported_at')
    readonly_fields = ('created_at', 'imported_at', 'transaction_count')
    ordering = ('-created_at',)
    show_change_link = True
    verbose_name_plural = '📄 Documents'


# ── UserAdmin ───────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'full_name', 'is_staff', 'is_active',
        'tx_count', 'date_joined', 'delete_btn'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'date_joined'

    fieldsets = (
        ('Compte', {'fields': ('username', 'password')}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'locale', 'currency')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Dates', {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    inlines = [
        CategoryInline,
        TransactionInline,
        SavingsAccountInline,
        SavingsRuleInline,
        GoalInline,
        NotificationInline,
        DocumentInline,
    ]

    @admin.display(description='Nom complet')
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip() or '—'

    @admin.display(description='Transactions')
    def tx_count(self, obj):
        count = obj.transactions.count()
        color = '#4ade80' if count > 0 else '#888'
        return format_html('<span style="color:{};">{}</span>', color, count)

    @admin.display(description='')
    def delete_btn(self, obj):
        from django.urls import reverse
        url = reverse('admin:users_user_delete', args=[obj.pk])
        return format_html(
            '<a href="{}" class="btn btn-sm btn-danger" '
            'style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:6px;'
            'font-size:0.75rem;font-weight:600;text-decoration:none;white-space:nowrap;"'
            'onclick="return confirm(\'Supprimer {} ?\')">🗑 Supprimer</a>',
            url, obj.username
        )
