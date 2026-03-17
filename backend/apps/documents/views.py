from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Document
from .serializers import DocumentSerializer
from .services.parser import parse_file
from apps.transactions.models import Transaction
from apps.transactions.services.categorization import compute_import_hash


class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class DocumentPreviewView(APIView):
    def get(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document non trouvé."}, status=404)

        transactions = parse_file(doc.file.path, doc.file_type)
        # Mark duplicates
        for t in transactions:
            t['is_duplicate'] = Transaction.objects.filter(import_hash=t['import_hash']).exists()

        return Response({
            "document_id": doc.id,
            "file_type": doc.file_type,
            "transactions": transactions,
            "total": len(transactions),
            "duplicates": sum(1 for t in transactions if t['is_duplicate']),
        })


class DocumentImportView(APIView):
    def post(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document non trouvé."}, status=404)

        selected = request.data.get('transactions', [])
        imported = 0
        skipped = 0

        for txn_data in selected:
            import_hash = txn_data.get('import_hash')
            if Transaction.objects.filter(import_hash=import_hash).exists():
                skipped += 1
                continue

            from apps.categories.models import Category
            category = None
            cat_name = txn_data.get('category') or txn_data.get('suggested_category', 'Autre')
            cat_obj = Category.objects.filter(user=request.user, name=cat_name).first()

            Transaction.objects.create(
                user=request.user,
                category=cat_obj,
                amount=txn_data['amount'],
                label=txn_data['label'],
                date=txn_data['date'],
                type=txn_data.get('type', 'expense'),
                source='import',
                import_hash=import_hash,
            )
            imported += 1

        doc.status = 'imported'
        doc.imported_at = timezone.now()
        doc.transaction_count = imported
        doc.save()

        return Response({
            "imported": imported,
            "skipped": skipped,
            "message": f"{imported} transaction(s) importée(s), {skipped} doublon(s) ignoré(s)."
        })
