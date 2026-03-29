from rest_framework import serializers
from .models import BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            'id', 'name', 'bank_name', 'account_type',
            'initial_balance', 'color', 'icon', 'is_default',
            'balance', 'transaction_count', 'created_at',
        ]
        read_only_fields = ['created_at', 'balance', 'transaction_count']

    def get_balance(self, obj):
        from django.db.models import Sum
        from decimal import Decimal
        from apps.transactions.models import Transaction
        qs = Transaction.objects.filter(bank_account=obj)
        income   = qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        expenses = qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        savings  = qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        return float(obj.initial_balance + income - expenses - savings)

    def get_transaction_count(self, obj):
        from apps.transactions.models import Transaction
        return Transaction.objects.filter(bank_account=obj).count()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # If first account or marked default → unset other defaults
        if validated_data.get('is_default'):
            BankAccount.objects.filter(user=validated_data['user'], is_default=True).update(is_default=False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('is_default'):
            BankAccount.objects.filter(
                user=instance.user, is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)
