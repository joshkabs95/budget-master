from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'file_type', 'status', 'imported_at', 'transaction_count', 'created_at']
        read_only_fields = ['status', 'imported_at', 'transaction_count', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        file = validated_data.get('file')
        if file:
            name = file.name.lower()
            if name.endswith('.pdf'):
                validated_data['file_type'] = 'pdf'
            elif name.endswith('.csv'):
                validated_data['file_type'] = 'csv'
        return super().create(validated_data)
