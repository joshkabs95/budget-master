from datetime import date
from rest_framework import serializers
from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    horizon = serializers.ReadOnlyField()
    progress = serializers.SerializerMethodField()
    monthly_required = serializers.SerializerMethodField()
    current_amount = serializers.SerializerMethodField()
    months_to_goal = serializers.SerializerMethodField()
    savings_account_detail = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            'id', 'savings_account', 'savings_account_detail',
            'name', 'type', 'target_amount', 'current_amount', 'deadline',
            'icon', 'color', 'horizon', 'progress', 'monthly_required',
            'months_to_goal', 'created_at',
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_current_amount(self, obj):
        return obj.get_effective_amount()

    def get_progress(self, obj):
        effective = obj.get_effective_amount()
        if obj.target_amount > 0:
            return round(effective / float(obj.target_amount) * 100, 1)
        return 0.0

    def get_monthly_required(self, obj):
        today = date.today()
        delta_days = (obj.deadline - today).days
        if delta_days <= 0:
            return 0.0
        months_left = max(1, delta_days / 30)
        remaining = float(obj.target_amount) - obj.get_effective_amount()
        return round(max(0, remaining) / months_left, 2)

    def get_savings_account_detail(self, obj):
        if obj.savings_account:
            return {
                'id': obj.savings_account.id,
                'name': obj.savings_account.name,
                'icon': obj.savings_account.icon,
                'color': obj.savings_account.color,
            }
        return None

    def get_months_to_goal(self, obj):
        effective = obj.get_effective_amount()
        if effective >= float(obj.target_amount):
            return 0
        remaining = float(obj.target_amount) - effective
        try:
            today = date.today()
            from django.db.models import Sum
            from apps.transactions.models import Transaction
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
