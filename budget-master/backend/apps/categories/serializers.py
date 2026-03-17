from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    spent_this_month = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, required=False, default=0)

    class Meta:
        model = Category
        fields = ('id', 'name', 'icon', 'color', 'type', 'budget_limit', 'rule_bucket', 'created_at', 'spent_this_month')
        read_only_fields = ('id', 'created_at')
