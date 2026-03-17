from rest_framework import serializers
from .models import Transaction
from apps.categories.serializers import CategorySerializer

class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'category', 'category_detail', 'savings_account',
            'amount', 'label', 'date', 'type', 'source', 'import_hash', 'created_at'
        ]
        read_only_fields = ['created_at', 'import_hash']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        if data.get('type') == 'saving' and not data.get('savings_account'):
            raise serializers.ValidationError("savings_account est requis pour une transaction de type 'saving'.")
        return data
