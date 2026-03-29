from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from datetime import date
from .models import Category, CategoryBudget, CategoryRule
from .serializers import CategorySerializer, CategoryBudgetSerializer, CategoryRuleSerializer
from apps.transactions.models import Transaction


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        today = date.today()
        month_str = f"{today.year}-{today.month:02d}"
        return Category.objects.filter(user=self.request.user).annotate(
            _month_spending=Coalesce(
                Sum(
                    'transaction__amount',
                    filter=Q(
                        transaction__user=self.request.user,
                        transaction__date__startswith=month_str,
                        transaction__type='expense',
                    ),
                ),
                0,
                output_field=DecimalField(),
            )
        )

    @action(detail=True, methods=['post'])
    def merge_into(self, request, pk=None):
        """
        Merge this category into another (target).
        All transactions from `pk` are reassigned to `target_id`.
        Then `pk` category is deleted.
        """
        source = self.get_object()
        target_id = request.data.get('target_id')
        if not target_id:
            return Response({'error': 'target_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = Category.objects.get(id=target_id, user=request.user)
        except Category.DoesNotExist:
            return Response({'error': 'Catégorie cible introuvable'}, status=status.HTTP_404_NOT_FOUND)
        if source.id == target.id:
            return Response({'error': 'Source et cible identiques'}, status=status.HTTP_400_BAD_REQUEST)

        count = Transaction.objects.filter(user=request.user, category=source).update(category=target)
        source.delete()
        return Response({'merged': count, 'target': target.name})


class CategoryBudgetViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryBudgetSerializer

    def get_queryset(self):
        qs = CategoryBudget.objects.filter(user=self.request.user).select_related('category')
        month = self.request.query_params.get('month')
        if month:
            qs = qs.filter(month=month).annotate(
                _spent=Coalesce(
                    Sum(
                        'category__transaction__amount',
                        filter=Q(
                            category__transaction__user=self.request.user,
                            category__transaction__date__startswith=month,
                            category__transaction__type='expense',
                        ),
                    ),
                    0,
                    output_field=DecimalField(),
                )
            )
        return qs

    def list(self, request, *args, **kwargs):
        month = request.query_params.get('month')
        if month:
            self._auto_init_month(month)
        return super().list(request, *args, **kwargs)

    def _auto_init_month(self, month):
        """Auto-create envelopes for all wants categories for a given month.

        - Copies allocated + carry-over from previous month when available.
        - Creates a blank envelope (allocated=0) for any wants category not yet covered.
        """
        user = self.request.user

        year, m = map(int, month.split('-'))
        prev_month = f"{year - 1 if m == 1 else year}-{str(12 if m == 1 else m - 1).zfill(2)}"

        # Build carry-over from previous month
        prev_budgets = {pb.category_id: pb for pb in CategoryBudget.objects.filter(user=user, month=prev_month)}

        # All wants categories for this user
        wants_cats = list(Category.objects.filter(user=user, rule_bucket='wants'))

        for cat in wants_cats:
            if CategoryBudget.objects.filter(user=user, category=cat, month=month).exists():
                continue  # already created (e.g. via upsert)

            prev = prev_budgets.get(cat.id)
            if prev:
                spent = Transaction.objects.filter(
                    user=user, category=cat, date__startswith=prev_month, type='expense',
                ).aggregate(total=Sum('amount'))['total'] or 0
                remaining = float(prev.allocated) + float(prev.carried_over) - float(spent)
                carry = max(remaining, 0)
                allocated = prev.allocated
            else:
                # No history: seed allocated from actual spending this month
                spent_now = Transaction.objects.filter(
                    user=user, category=cat, date__startswith=month, type='expense',
                ).aggregate(total=Sum('amount'))['total'] or 0
                if not spent_now:
                    continue  # No spending, no previous budget → skip
                carry = 0
                allocated = abs(float(spent_now))

            CategoryBudget.objects.create(
                user=user,
                category=cat,
                month=month,
                allocated=allocated,
                carried_over=carry,
            )

    @action(detail=False, methods=['post'])
    def upsert(self, request):
        """Create or update an envelope for a category/month."""
        category_id = request.data.get('category')
        month = request.data.get('month')
        allocated = request.data.get('allocated', 0)

        if not category_id or not month:
            return Response({'error': 'category and month are required'}, status=status.HTTP_400_BAD_REQUEST)

        budget, created = CategoryBudget.objects.get_or_create(
            user=request.user,
            category_id=category_id,
            month=month,
            defaults={'allocated': allocated},
        )
        if not created:
            budget.allocated = allocated
            budget.save(update_fields=['allocated'])

        serializer = self.get_serializer(budget)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CategoryRuleViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryRuleSerializer

    def get_queryset(self):
        return CategoryRule.objects.filter(user=self.request.user).select_related('category')
