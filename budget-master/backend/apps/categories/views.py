from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from .models import Category
from .serializers import CategorySerializer
from apps.transactions.models import Transaction


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user)
        cat_type = self.request.query_params.get('type')
        if cat_type:
            qs = qs.filter(type=cat_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        return serializer

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response
        queryset = self.get_queryset()
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        categories_data = []
        for cat in queryset:
            spent = Transaction.objects.filter(
                user=request.user,
                category=cat,
                type='expense',
                date__gte=month_start.date()
            ).aggregate(total=Sum('amount'))['total'] or 0

            cat_data = CategorySerializer(cat).data
            cat_data['spent_this_month'] = float(spent)
            categories_data.append(cat_data)

        return Response(categories_data)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
