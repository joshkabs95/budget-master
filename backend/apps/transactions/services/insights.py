from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum


def generate_insights(user) -> list:
    from apps.transactions.models import Transaction
    from apps.savings.models import SavingsRule

    insights = []
    today = date.today()
    first_of_month = today.replace(day=1)

    month_txns = Transaction.objects.filter(user=user, date__gte=first_of_month)
    income   = month_txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    expenses = month_txns.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    savings  = month_txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

    if income > 0:
        savings_rate = (savings / income) * 100

        # ── Budget alerts (budget_limit) ─────────────────────────────────────
        from apps.categories.models import Category, CategoryBudget
        next_month = (first_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        days_left = (next_month - today).days
        categories = Category.objects.filter(user=user, budget_limit__isnull=False)
        for cat in categories:
            cat_spent = month_txns.filter(type='expense', category=cat).aggregate(s=Sum('amount'))['s'] or Decimal('0')
            if cat.budget_limit and cat.budget_limit > 0:
                ratio = float(cat_spent / cat.budget_limit * 100)
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
                        "message": f"Budget {cat.name} à {ratio:.0f}% — {days_left}j restants ce mois",
                        "category": cat.name,
                    })

        # ── Envelope (YNAB) alerts ───────────────────────────────────────────
        month_str = today.strftime('%Y-%m')
        envelopes = CategoryBudget.objects.filter(
            user=user, month=month_str, allocated__gt=0
        ).select_related('category')
        for env in envelopes:
            cat_spent = month_txns.filter(
                type='expense', category=env.category
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
            total_budget = env.allocated + env.carried_over
            if total_budget <= 0:
                continue
            ratio = float(cat_spent / total_budget * 100)
            cat_name = env.category.name
            if ratio >= 100:
                insights.append({
                    "type": "budget_exceeded",
                    "severity": "red",
                    "message": f"Enveloppe {cat_name} dépassée ({ratio:.0f}%) — {float(cat_spent):.0f}€ / {float(total_budget):.0f}€",
                    "category": cat_name,
                })
            elif ratio >= 80:
                remaining = float(total_budget - cat_spent)
                insights.append({
                    "type": "budget_warning",
                    "severity": "orange",
                    "message": f"Enveloppe {cat_name} à {ratio:.0f}% — {remaining:.0f}€ restants ({days_left}j)",
                    "category": cat_name,
                })

        # ── Savings gap ──────────────────────────────────────────────────────
        try:
            rule = SavingsRule.objects.get(user=user, active=True)
            gap = float(rule.savings_target) - float(savings_rate)
            if gap > 0:
                insights.append({
                    "type": "savings_gap",
                    "severity": "orange" if gap < 5 else "red",
                    "message": f"Épargne à {savings_rate:.1f}% (cible {rule.savings_target}%). "
                               f"Réduire les Envies de {gap:.1f}% peut combler l'écart.",
                })
        except SavingsRule.DoesNotExist:
            pass

        # ── Anomaly detection ────────────────────────────────────────────────
        insights.extend(_detect_anomalies(user, month_txns, today))

    # ── Risk score (fin de mois) ─────────────────────────────────────────────
    risk_insight = _compute_risk_insight(user, income, expenses, savings, today)
    if risk_insight:
        insights.append(risk_insight)

    # ── Streak ───────────────────────────────────────────────────────────────
    streak = _compute_savings_streak(user)
    if streak > 0:
        insights.append({
            "type": "streak",
            "severity": "green",
            "message": f"Streak : règle d'épargne respectée {streak} mois consécutifs 🎉",
            "streak": streak,
        })

    return insights


def _detect_anomalies(user, month_txns, today) -> list:
    """Détecte les catégories où la dépense ce mois est > 2x la moyenne des 3 derniers mois."""
    from apps.transactions.models import Transaction

    # Build 3-month category averages
    past_months = []
    for i in range(1, 4):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12; y -= 1
        past_months.append((y, m))

    cat_avg = {}
    for cat_id, cat_name, cat_icon in (
        month_txns.filter(type='expense')
        .values_list('category_id', 'category__name', 'category__icon')
        .distinct()
    ):
        if not cat_id:
            continue
        monthly_totals = []
        for y, m in past_months:
            total = Transaction.objects.filter(
                user=user, type='expense', category_id=cat_id,
                date__year=y, date__month=m,
            ).aggregate(s=Sum('amount'))['s']
            if total:
                monthly_totals.append(float(total))
        if monthly_totals:
            cat_avg[cat_id] = (sum(monthly_totals) / len(monthly_totals), cat_name, cat_icon or '')

    insights = []
    for row in (
        month_txns.filter(type='expense')
        .values('category_id', 'category__name', 'category__icon')
        .annotate(total=Sum('amount'))
    ):
        cat_id = row['category_id']
        if not cat_id or cat_id not in cat_avg:
            continue
        avg, cat_name, cat_icon = cat_avg[cat_id]
        current = float(row['total'])
        if avg > 0 and current >= avg * 2.0:
            ratio = current / avg
            insights.append({
                "type": "anomaly",
                "severity": "red" if ratio >= 3.0 else "orange",
                "message": (
                    f"⚠️ Anomalie {cat_icon} {cat_name} : {current:.0f}€ ce mois "
                    f"vs moyenne {avg:.0f}€ ({ratio:.1f}x)"
                ),
                "category": cat_name,
            })
    return insights


def _compute_risk_insight(user, income, expenses, savings, today) -> dict | None:
    """Score de risque fin de mois basé sur la projection du ForecastEngine."""
    try:
        from apps.forecasting.engine import ForecastEngine
        engine = ForecastEngine(user)
        proj = engine.project(1)
        if not proj:
            return None
        p = proj[0]
        net = p['net']
        proj_income = p['projected_income']
        proj_expenses = p['projected_expenses']

        if net > 0 and proj_expenses < proj_income * 0.85:
            risk, severity = 'low', 'green'
            msg = f"Risque fin de mois : 🟢 Faible — solde estimé +{net:.0f}€"
        elif net > 0:
            risk, severity = 'medium', 'orange'
            msg = f"Risque fin de mois : 🟡 Modéré — solde estimé +{net:.0f}€ (dépenses proches des revenus)"
        elif net > -300:
            risk, severity = 'medium', 'orange'
            msg = f"Risque fin de mois : 🟡 Modéré — solde estimé {net:.0f}€"
        else:
            risk, severity = 'high', 'red'
            msg = f"Risque fin de mois : 🔴 Élevé — solde estimé {net:.0f}€"

        return {"type": "risk_score", "severity": severity, "message": msg, "risk": risk}
    except Exception:
        return None


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
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12; y -= 1
        first = date(y, m, 1)
        next_m = m % 12 + 1
        next_y = y if next_m != 1 else y + 1
        last = date(next_y, next_m, 1) - timedelta(days=1)

        txns = Transaction.objects.filter(user=user, date__range=[first, last])
        inc  = txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        sav  = txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

        if inc > 0 and float(sav / inc * 100) >= float(rule.savings_target):
            streak += 1
        else:
            break
    return streak
