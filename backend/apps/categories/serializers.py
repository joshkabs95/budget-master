from rest_framework import serializers
from django.db.models import Sum
from .models import Category, CategoryBudget, CategoryRule
from apps.transactions.models import Transaction


class CategorySerializer(serializers.ModelSerializer):
    month_spending = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'type', 'budget_limit', 'rule_bucket', 'created_at', 'month_spending']
        read_only_fields = ['created_at', 'month_spending']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_month_spending(self, obj):
        if hasattr(obj, '_month_spending'):
            return float(obj._month_spending)
        from datetime import date
        today = date.today()
        month_str = f"{today.year}-{today.month:02d}"
        result = Transaction.objects.filter(
            user=obj.user,
            category=obj,
            date__startswith=month_str,
            type='expense',
        ).aggregate(total=Sum('amount'))
        return float(result['total'] or 0)


class CategoryBudgetSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = CategoryBudget
        fields = ['id', 'category', 'category_detail', 'month', 'allocated', 'carried_over', 'spent', 'remaining']
        read_only_fields = ['carried_over']

    def get_spent(self, obj):
        if hasattr(obj, '_spent'):
            return float(obj._spent)
        result = Transaction.objects.filter(
            user=obj.user,
            category=obj.category,
            date__startswith=obj.month,
            type='expense',
        ).aggregate(total=Sum('amount'))
        return float(result['total'] or 0)

    def get_remaining(self, obj):
        return float(obj.allocated) + float(obj.carried_over) - self.get_spent(obj)


class CategoryRuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)

    class Meta:
        model = CategoryRule
        fields = ['id', 'keyword', 'category', 'category_name', 'category_icon', 'priority']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
