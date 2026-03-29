from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone


@dataclass
class WantsEnvelope:
    category_id: int
    label: str
    icon: str
    score: int        # 1-5
    weight_pct: float
    envelope: Decimal
    spent: Decimal
    remaining: Decimal
    status: str       # green / yellow / red


DEFAULT_SCORE = 3


class WantsAllocator:
    def __init__(self, user, wants_budget: Decimal):
        self.user = user
        self.wants_budget = wants_budget

    def compute_envelopes(self, scores: dict) -> list:
        """
        scores = {str(category_id): int_score, ...}
        Uses only user's categories with rule_bucket='wants'
        """
        from apps.categories.models import Category

        wants_cats = list(
            Category.objects.filter(user=self.user, rule_bucket='wants', type='expense')
        )
        if not wants_cats:
            return []

        total_score = sum(int(scores.get(str(c.id), DEFAULT_SCORE)) for c in wants_cats)
        if total_score == 0:
            total_score = 1

        today = timezone.now().date()
        envelopes = []

        for cat in wants_cats:
            score = int(scores.get(str(cat.id), DEFAULT_SCORE))
            weight_pct = score / total_score
            envelope = self.wants_budget * Decimal(str(round(weight_pct, 6)))

            spent_agg = __import__('apps.transactions.models', fromlist=['Transaction']).Transaction.objects.filter(
                user=self.user,
                category=cat,
                type='expense',
                date__year=today.year,
                date__month=today.month,
            ).aggregate(s=Sum('amount'))['s']
            spent = Decimal(str(spent_agg or 0))
            remaining = envelope - spent

            ratio = spent / envelope if envelope > 0 else Decimal(0)
            if ratio <= Decimal('0.75'):
                status = 'green'
            elif ratio <= Decimal('1.00'):
                status = 'yellow'
            else:
                status = 'red'

            envelopes.append(WantsEnvelope(
                category_id=cat.id,
                label=str(cat),
                icon=cat.icon,
                score=score,
                weight_pct=round(weight_pct * 100, 1),
                envelope=round(envelope, 2),
                spent=round(spent, 2),
                remaining=round(remaining, 2),
                status=status,
            ))

        envelopes.sort(key=lambda e: e.score, reverse=True)
        return envelopes
