from rest_framework import serializers
from .models import SavingsAccount, SavingsRule

class SavingsAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsAccount
        fields = ['id', 'name', 'initial_balance', 'target', 'interest_rate', 'color', 'icon', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class SavingsRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsRule
        fields = [
            'id', 'savings_target', 'needs_target', 'wants_target',
            'savings_tolerance', 'needs_tolerance', 'wants_tolerance',
            'savings_floor', 'needs_floor', 'wants_floor',
            'compensation_order', 'window_months', 'catchup_max_months',
            'mode', 'active', 'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
