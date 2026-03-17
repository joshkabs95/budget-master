from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Document
from .serializers import DocumentSerializer
from .services.parser import parse_csv, parse_pdf
from apps.transactions.models import Transaction
from apps.categories.models import Category


class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if not file:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'file': 'Fichier requis.'})

        file_type = 'pdf' if file.name.lower().endswith('.pdf') else 'csv'
        serializer.save(user=self.request.user, file_type=file_type)


class DocumentPreviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({'detail': 'Document non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        if doc.file_type == 'csv':
            content = doc.file.read()
            transactions = parse_csv(content, request.user)
        else:
            transactions = parse_pdf(doc.file.path, request.user)

        # Check for duplicates
        for t in transactions:
            t['is_duplicate'] = Transaction.objects.filter(
                user=request.user,
                import_hash=t['import_hash']
            ).exists()
            t['date'] = str(t['date'])

        return Response({'transactions': transactions, 'count': len(transactions)})


class DocumentImportView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            doc = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({'detail': 'Document non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        if doc.status == 'imported':
            return Response({'detail': 'Document déjà importé.'}, status=status.HTTP_400_BAD_REQUEST)

        if doc.file_type == 'csv':
            content = doc.file.read()
            transactions = parse_csv(content, request.user)
        else:
            transactions = parse_pdf(doc.file.path, request.user)

        imported_count = 0
        skipped_count = 0

        for t in transactions:
            # Skip duplicates
            if Transaction.objects.filter(user=request.user, import_hash=t['import_hash']).exists():
                skipped_count += 1
                continue

            # Find or create category
            cat = None
            if t['category_name'] != 'Autre':
                cat = Category.objects.filter(user=request.user, name=t['category_name']).first()

            Transaction.objects.create(
                user=request.user,
                category=cat,
                amount=t['amount'],
                label=t['label'],
                date=t['date'],
                type=t['type'],
                source='import',
                import_hash=t['import_hash'],
            )
            imported_count += 1

        doc.status = 'imported'
        doc.imported_at = timezone.now()
        doc.transaction_count = imported_count
        doc.save()

        return Response({
            'imported': imported_count,
            'skipped': skipped_count,
            'document': DocumentSerializer(doc).data,
        })
