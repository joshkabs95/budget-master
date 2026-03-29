from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum
from decimal import Decimal
from .engine import ForecastEngine
from .budget_projector import BudgetProjector


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_forecast(request):
    horizon = min(int(request.query_params.get('months', 6)), 12)
    engine = ForecastEngine(request.user)
    projector = BudgetProjector(request.user, engine)

    # Current month actuals (M-0)
    from apps.transactions.models import Transaction
    from datetime import date as _date
    today = _date.today()
    qs0 = Transaction.objects.filter(user=request.user, date__year=today.year, date__month=today.month)
    cur_income   = float(qs0.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
    cur_expenses = float(qs0.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
    cur_savings  = float(qs0.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)
    cur_month_str = f'{today.year}-{today.month:02d}'

    # Real history (chronological): M-6 … M-1 + M-0
    raw_history = engine.monthly_history(6)
    history_out = []
    for h in reversed(raw_history):
        income = h['income']
        savings = h['savings']
        history_out.append({
            'month': h['month'],
            'is_forecast': False,
            'income': income,
            'expenses': h['expenses'],
            'savings': savings,
            'net': h['net'],
            'savings_pct': round(savings / income * 100 if income else 0, 1),
        })
    # Append current month
    history_out.append({
        'month': cur_month_str,
        'is_forecast': False,
        'income': cur_income,
        'expenses': cur_expenses,
        'savings': cur_savings,
        'net': cur_income - cur_expenses - cur_savings,
        'savings_pct': round(cur_savings / cur_income * 100 if cur_income else 0, 1),
    })

    data = projector.project_buckets(horizon)

    return Response({
        'history': history_out,
        **data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate(request):
    """
    Simulation "What If".
    Body: { "reductions": {"<category_id>": <amount_eur>}, "extra_savings": <amount_eur> }
    Returns before/after comparison for current month.
    """
    from apps.transactions.models import Transaction
    from apps.categories.models import Category
    from datetime import date

    user = request.user
    today = date.today()
    reductions = request.data.get('reductions', {})   # {str(cat_id): float}
    extra_savings = float(request.data.get('extra_savings', 0))

    # Current month actuals
    qs = Transaction.objects.filter(user=user, date__year=today.year, date__month=today.month)
    income   = float(qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
    expenses = float(qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
    savings  = float(qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)

    # 50/30/20 buckets — before
    by_cat = list(
        qs.filter(type='expense')
        .values('category__id', 'category__name', 'category__icon',
                'category__color', 'category__rule_bucket')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    bucket_totals = {'needs': 0.0, 'wants': 0.0}
    for row in by_cat:
        bucket = row['category__rule_bucket'] or 'wants'
        if bucket in bucket_totals:
            bucket_totals[bucket] += float(row['total'] or 0)

    def rule_pcts(inc, need, want, sav):
        if inc <= 0:
            return {'needs': 0, 'wants': 0, 'savings': 0}
        return {
            'needs':   round(need / inc * 100, 1),
            'wants':   round(want / inc * 100, 1),
            'savings': round(sav  / inc * 100, 1),
        }

    def compute_risk(inc, exp, sav):
        if inc <= 0:
            return 'high'
        ratio = (exp + sav) / inc
        if ratio < 0.85:
            return 'low'
        elif ratio < 1.0:
            return 'medium'
        return 'high'

    before = {
        'income': round(income, 2),
        'expenses': round(expenses, 2),
        'savings': round(savings, 2),
        'balance': round(income - expenses - savings, 2),
        'rule_503020': rule_pcts(income, bucket_totals['needs'], bucket_totals['wants'], savings),
        'risk': compute_risk(income, expenses, savings),
        'by_category': [
            {
                'id': r['category__id'],
                'name': r['category__name'],
                'icon': r['category__icon'],
                'color': r['category__color'],
                'bucket': r['category__rule_bucket'] or 'wants',
                'total': round(float(r['total'] or 0), 2),
            }
            for r in by_cat
        ],
    }

    # Apply simulated reductions
    total_reduction = 0.0
    new_bucket_totals = dict(bucket_totals)
    adjusted_cats = []
    for row in by_cat:
        cat_id = str(row['category__id'])
        reduction = float(reductions.get(cat_id, 0))
        current = float(row['total'] or 0)
        new_total = max(0.0, current - reduction)
        total_reduction += (current - new_total)
        bucket = row['category__rule_bucket'] or 'wants'
        if bucket in new_bucket_totals:
            new_bucket_totals[bucket] -= (current - new_total)
        adjusted_cats.append({**row, 'total': new_total, 'reduction': round(current - new_total, 2)})

    new_expenses = max(0.0, expenses - total_reduction)
    new_savings  = savings + extra_savings
    new_balance  = income - new_expenses - new_savings

    after = {
        'income': round(income, 2),
        'expenses': round(new_expenses, 2),
        'savings': round(new_savings, 2),
        'balance': round(new_balance, 2),
        'rule_503020': rule_pcts(income, new_bucket_totals['needs'], new_bucket_totals['wants'], new_savings),
        'risk': compute_risk(income, new_expenses, new_savings),
    }

    impact = {
        'expense_reduction': round(total_reduction, 2),
        'savings_gain': round(new_savings - savings, 2),
        'balance_delta': round(new_balance - (income - expenses - savings), 2),
        'savings_rate_before': round(savings / income * 100 if income else 0, 1),
        'savings_rate_after':  round(new_savings / income * 100 if income else 0, 1),
        'risk_change': f"{before['risk']} → {after['risk']}",
    }

    return Response({'before': before, 'after': after, 'impact': impact})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def wants_envelopes(request):
    """
    GET  → return envelopes with current scores
    POST → {"scores": {"42": 4, "17": 5, ...}} → save scores & return new envelopes
    """
    from apps.savings.models import SavingsRule
    from apps.transactions.models import Transaction
    from .wants_allocator import WantsAllocator
    from django.utils import timezone

    # Get wants budget = income * wants_target% for current month
    today = timezone.now().date()
    income = Transaction.objects.filter(
        user=request.user,
        type='income',
        date__year=today.year,
        date__month=today.month,
    ).aggregate(s=Sum('amount'))['s'] or Decimal(0)

    rule = SavingsRule.objects.filter(user=request.user, active=True).first()
    wants_pct = Decimal(str(rule.wants_target)) / 100 if rule else Decimal('0.30')
    wants_budget = income * wants_pct

    scores = {}
    if rule:
        scores = rule.wants_scores or {}

    if request.method == 'POST':
        new_scores = request.data.get('scores', {})
        # Validate: scores must be int 1-5
        validated = {}
        for k, v in new_scores.items():
            try:
                s = max(1, min(5, int(v)))
                validated[str(k)] = s
            except (ValueError, TypeError):
                pass
        if rule and validated:
            rule.wants_scores = {**scores, **validated}
            rule.save(update_fields=['wants_scores'])
            scores = rule.wants_scores

    allocator = WantsAllocator(request.user, wants_budget)
    envelopes = allocator.compute_envelopes(scores)

    def _coaching(e) -> str | None:
        if e.score == 0 or e.envelope == 0:
            return None
        usage_pct = (e.spent / e.envelope * 100) if e.envelope > 0 else 0
        # Over budget — priorité absolue, peu importe le score
        if usage_pct > 100:
            return f"Enveloppe dépassée à {usage_pct:.0f}% — envisage de revoir le montant alloué."
        # High priority, low usage
        if e.score >= 4 and usage_pct < 30:
            return f"Priorité {e.score}/5 mais seulement {usage_pct:.0f}% utilisé — tu sous-consommes cette enveloppe."
        # Low priority, approaching limit (75–100%)
        if e.score <= 2 and usage_pct > 75:
            return f"Priorité {e.score}/5 mais {usage_pct:.0f}% consommé — cette catégorie approche ton plafond."
        return None

    return Response({
        'wants_budget': float(wants_budget),
        'income': float(income),
        'wants_pct': float(wants_pct * 100),
        'envelopes': [
            {
                'category_id': e.category_id,
                'label': e.label,
                'icon': e.icon,
                'score': e.score,
                'weight_pct': e.weight_pct,
                'envelope': float(e.envelope),
                'spent': float(e.spent),
                'remaining': float(e.remaining),
                'status': e.status,
                'coaching': _coaching(e),
            }
            for e in envelopes
        ],
    })
