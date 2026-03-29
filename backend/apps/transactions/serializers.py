from rest_framework import serializers
from .models import Transaction
from apps.categories.serializers import CategorySerializer

class BankAccountMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()


class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    goal_name = serializers.CharField(source='goal.name', read_only=True, default=None)
    goal_icon = serializers.CharField(source='goal.icon', read_only=True, default=None)
    bank_account_detail = BankAccountMiniSerializer(source='bank_account', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'category', 'category_detail', 'savings_account',
            'bank_account', 'bank_account_detail',
            'goal', 'goal_name', 'goal_icon',
            'amount', 'label', 'date', 'type', 'source', 'import_hash',
            'notes', 'is_recurring', 'recurrence', 'created_at'
        ]
        read_only_fields = ['created_at', 'import_hash']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        # On PATCH, merge with existing instance values before validating
        instance = getattr(self, 'instance', None)
        txn_type = data.get('type', instance.type if instance else None)
        account = data.get('savings_account', instance.savings_account if instance else None)
        if txn_type == 'saving' and not account:
            raise serializers.ValidationError("savings_account est requis pour une transaction de type 'saving'.")
        return data
