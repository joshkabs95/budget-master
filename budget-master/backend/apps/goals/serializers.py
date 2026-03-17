from rest_framework import serializers
from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    horizon = serializers.CharField(read_only=True)
    progress_pct = serializers.FloatField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = Goal
        fields = (
            'id', 'savings_account', 'name', 'type', 'target_amount',
            'current_amount', 'deadline', 'icon', 'color', 'created_at',
            'horizon', 'progress_pct', 'days_remaining'
        )
        read_only_fields = ('id', 'created_at')
