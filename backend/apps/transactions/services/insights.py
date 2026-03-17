from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth


def generate_insights(user) -> list:
    """Generate automatic behavioral insights for the user."""
    from apps.transactions.models import Transaction
    from apps.categories.models import Category
    from apps.savings.models import SavingsRule

    insights = []
    today = date.today()
    first_of_month = today.replace(day=1)

    # Monthly income & expenses
    month_txns = Transaction.objects.filter(user=user, date__gte=first_of_month)
    income = month_txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    expenses = month_txns.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    savings = month_txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

    if income > 0:
        savings_rate = (savings / income) * 100

        # Budget categories at 80%+
        categories = Category.objects.filter(user=user, budget_limit__isnull=False)
        for cat in categories:
            cat_spent = month_txns.filter(type='expense', category=cat).aggregate(s=Sum('amount'))['s'] or Decimal('0')
            if cat.budget_limit and cat.budget_limit > 0:
                ratio = float(cat_spent / cat.budget_limit * 100)
                days_left = (first_of_month.replace(month=first_of_month.month % 12 + 1) - today).days
                if ratio >= 100:
                    insights.append({
                        "type": "budget_exceeded",
                        "severity": "red",
                        "message": f"Budget {cat.name} dépassé ({ratio:.0f}%) — {cat_spent:.0f}€ / {cat.budget_limit:.0f}€",
                        "category": cat.name,
                    })
                elif ratio >= 80:
                    insights.append({
                        "type": "budget_warning",
                        "severity": "orange",
                        "message": f"Budget {cat.name} à {ratio:.0f}% — {days_left} jours restants ce mois",
                        "category": cat.name,
                    })

        # Savings insight
        try:
            rule = SavingsRule.objects.get(user=user, active=True)
            gap = float(rule.savings_target) - float(savings_rate)
            if gap > 0:
                wants_txns = month_txns.filter(type='expense', category__rule_bucket='wants')
                wants_total = wants_txns.aggregate(s=Sum('amount'))['s'] or Decimal('0')
                wants_rate = float(wants_total / income * 100)
                insights.append({
                    "type": "savings_gap",
                    "severity": "orange" if gap < 5 else "red",
                    "message": f"Épargne à {savings_rate:.1f}% (cible {rule.savings_target}%). "
                               f"Réduire les Envies de {gap:.1f}% peut combler l'écart.",
                })
        except SavingsRule.DoesNotExist:
            pass

    # Streak: consecutive months with savings rule respected
    streak = _compute_savings_streak(user)
    if streak > 0:
        insights.append({
            "type": "streak",
            "severity": "green",
            "message": f"Streak : règle d'épargne respectée {streak} mois consécutifs 🎉",
            "streak": streak,
        })

    return insights


def _compute_savings_streak(user) -> int:
    from apps.transactions.models import Transaction
    from apps.savings.models import SavingsRule
    try:
        rule = SavingsRule.objects.get(user=user, active=True)
    except SavingsRule.DoesNotExist:
        return 0

    streak = 0
    today = date.today()
    for i in range(1, 7):
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        first = date(year, month, 1)
        last_month = month % 12 + 1
        last_year = year if last_month != 1 else year + 1
        last = date(last_year, last_month, 1) - timedelta(days=1)

        txns = Transaction.objects.filter(user=user, date__range=[first, last])
        income = txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        savings = txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

        if income > 0:
            rate = float(savings / income * 100)
            if rate >= float(rule.savings_target):
                streak += 1
            else:
                break
        else:
            break
    return streak
