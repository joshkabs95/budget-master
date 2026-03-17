from rest_framework import serializers
from .models import Goal

class GoalSerializer(serializers.ModelSerializer):
    horizon = serializers.ReadOnlyField()
    progress = serializers.ReadOnlyField()
    monthly_required = serializers.ReadOnlyField()

    class Meta:
        model = Goal
        fields = [
            'id', 'savings_account', 'name', 'type',
            'target_amount', 'current_amount', 'deadline',
            'icon', 'color', 'horizon', 'progress', 'monthly_required', 'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
