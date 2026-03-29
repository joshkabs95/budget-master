from rest_framework import serializers
from .models import ReconciliationSession, ReconciliationEntry
from apps.transactions.serializers import TransactionSerializer


class ReconciliationEntrySerializer(serializers.ModelSerializer):
    transaction_detail = TransactionSerializer(source='transaction', read_only=True)

    class Meta:
        model = ReconciliationEntry
        fields = [
            'id', 'transaction', 'transaction_detail',
            'bank_date', 'bank_label', 'bank_amount',
            'status', 'match_score',
        ]


class ReconciliationSessionSerializer(serializers.ModelSerializer):
    entries = ReconciliationEntrySerializer(many=True, read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationSession
        fields = ['id', 'month', 'status', 'created_at', 'closed_at', 'entries', 'stats']
        read_only_fields = ['created_at', 'closed_at', 'status']

    def get_stats(self, obj):
        entries = obj.entries.all()
        total = entries.count()
        auto = entries.filter(status='auto').count()
        manual = entries.filter(status='manual').count()
        unmatched_app = entries.filter(status='unmatched_app').count()
        unmatched_bank = entries.filter(status='unmatched_bank').count()
        return {
            'total': total,
            'auto': auto,
            'manual': manual,
            'unmatched_app': unmatched_app,
            'unmatched_bank': unmatched_bank,
            'matched_pct': round((auto + manual) / total * 100, 1) if total else 0,
        }
