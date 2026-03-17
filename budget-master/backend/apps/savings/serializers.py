from rest_framework import serializers
from .models import SavingsAccount, SavingsRule


class SavingsAccountSerializer(serializers.ModelSerializer):
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = SavingsAccount
        fields = ('id', 'name', 'balance', 'target', 'interest_rate', 'color', 'icon', 'created_at', 'progress_pct')
        read_only_fields = ('id', 'created_at', 'balance')

    def get_progress_pct(self, obj):
        if obj.target and float(obj.target) > 0:
            return round(float(obj.balance) / float(obj.target) * 100, 1)
        return None


class SavingsRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsRule
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at')
