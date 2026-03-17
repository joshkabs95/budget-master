from rest_framework import serializers
from .models import Transaction
from apps.categories.serializers import CategorySerializer
from apps.savings.serializers import SavingsAccountSerializer


class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    savings_account_detail = SavingsAccountSerializer(source='savings_account', read_only=True)

    class Meta:
        model = Transaction
        fields = (
            'id', 'category', 'category_detail', 'savings_account', 'savings_account_detail',
            'amount', 'label', 'date', 'type', 'source', 'import_hash', 'created_at'
        )
        read_only_fields = ('id', 'created_at', 'import_hash')

    def validate(self, data):
        if data.get('type') == 'saving' and not data.get('savings_account'):
            raise serializers.ValidationError({'savings_account': 'Un compte épargne est requis pour les transactions d\'épargne.'})
        return data
