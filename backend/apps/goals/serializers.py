from rest_framework import serializers
from .models import Goal

class GoalSerializer(serializers.ModelSerializer):
    horizon = serializers.ReadOnlyField()
    progress = serializers.ReadOnlyField()
    monthly_required = serializers.ReadOnlyField()
    months_to_goal = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            'id', 'savings_account', 'name', 'type',
            'target_amount', 'current_amount', 'deadline',
            'icon', 'color', 'horizon', 'progress', 'monthly_required',
            'months_to_goal', 'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_months_to_goal(self, obj):
        """
        Estimate months to reach goal based on average monthly savings (last 3 months).
        Returns None if no savings history, 0 if already reached.
        """
        if float(obj.progress) >= 100:
            return 0
        remaining = float(obj.target_amount) - float(obj.current_amount)
        if remaining <= 0:
            return 0
        try:
            from datetime import date
            from django.db.models import Sum
            from apps.transactions.models import Transaction
            today = date.today()
            totals = []
            for i in range(1, 4):
                m = today.month - i
                y = today.year
                if m <= 0:
                    m += 12; y -= 1
                month_str = f"{y}-{m:02d}"
                s = Transaction.objects.filter(
                    user=obj.user, type='saving', date__startswith=month_str
                ).aggregate(t=Sum('amount'))['t'] or 0
                totals.append(float(s))
            avg = sum(totals) / len([t for t in totals if t > 0]) if any(t > 0 for t in totals) else 0
            if avg <= 0:
                return None
            return round(remaining / avg)
        except Exception:
            return None
