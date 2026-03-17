from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'file', 'file_type', 'status', 'imported_at', 'transaction_count', 'created_at')
        read_only_fields = ('id', 'status', 'imported_at', 'transaction_count', 'created_at')
