from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta


def generate_insights(user):
    """Generate automatic behavioral insights for the user."""
    from apps.transactions.models import Transaction
    from apps.categories.models import Category
    from apps.goals.models import Goal
    from apps.savings.models import SavingsRule

    now = date.today()
    month_start = now.replace(day=1)

    qs_month = Transaction.objects.filter(user=user, date__gte=month_start)
    income = float(qs_month.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0)
    expenses = float(qs_month.filter(type='expense').aggregate(t=Sum('amount'))['t'] or 0)
    savings = float(qs_month.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0)

    insights = []

    # 1. Savings rate comparison
    target_rate = 20.0
    try:
        rule = user.savings_rule
        target_rate = float(rule.savings_target)
    except SavingsRule.DoesNotExist:
        pass

    if income > 0:
        savings_rate = (savings / income) * 100
        if savings_rate < target_rate:
            gap = target_rate - savings_rate
            insights.append({
                'type': 'warning',
                'title': "Taux d'épargne insuffisant",
                'message': f"Vous épargnez {savings_rate:.1f}% de vos revenus, soit {gap:.1f}% en dessous de l'objectif de {target_rate:.0f}%.",
                'icon': '⚠️',
                'data': {'current': savings_rate, 'target': target_rate, 'gap': gap}
            })
        else:
            insights.append({
                'type': 'success',
                'title': "Objectif d'épargne atteint !",
                'message': f"Excellent ! Vous épargnez {savings_rate:.1f}% de vos revenus, dépassant l'objectif de {target_rate:.0f}%.",
                'icon': '✅',
                'data': {'current': savings_rate, 'target': target_rate}
            })

    # 2. Budget categories at 80%+ of limit
    cats = Category.objects.filter(user=user, type='expense', budget_limit__isnull=False)
    alerts = []
    for cat in cats:
        spent = float(qs_month.filter(category=cat, type='expense').aggregate(t=Sum('amount'))['t'] or 0)
        limit = float(cat.budget_limit)
        if limit > 0:
            pct = (spent / limit) * 100
            if pct >= 80:
                alerts.append({'name': cat.name, 'icon': cat.icon, 'spent': spent, 'limit': limit, 'pct': round(pct, 1)})

    if alerts:
        for a in alerts:
            status = 'alert' if a['pct'] >= 100 else 'warning'
            insights.append({
                'type': status,
                'title': f"Budget {a['name']} {'dépassé' if a['pct'] >= 100 else 'proche du plafond'}",
                'message': f"{a['icon']} {a['name']}: {a['spent']:.0f}€ / {a['limit']:.0f}€ ({a['pct']}%)",
                'icon': '🔴' if a['pct'] >= 100 else '🟡',
                'data': a
            })

    # 3. Upcoming planned expenses (Goals type='expense' in next 6 weeks)
    six_weeks = now + timedelta(weeks=6)
    upcoming = Goal.objects.filter(
        user=user,
        type='expense',
        deadline__gte=now,
        deadline__lte=six_weeks
    )
    for goal in upcoming:
        remaining = float(goal.target_amount) - float(goal.current_amount)
        days = (goal.deadline - now).days
        insights.append({
            'type': 'info',
            'title': f"Dépense prévue dans {days} jours",
            'message': f"{goal.icon} {goal.name}: {remaining:.0f}€ encore nécessaires avant le {goal.deadline.strftime('%d/%m/%Y')}",
            'icon': '📅',
            'data': {'goal_id': goal.id, 'name': goal.name, 'remaining': remaining, 'days': days}
        })

    # 4. Savings streak (consecutive months meeting savings target)
    streak = 0
    check_date = now.replace(day=1) - timedelta(days=1)
    for _ in range(12):
        m_start = check_date.replace(day=1)
        m_qs = Transaction.objects.filter(user=user, date__gte=m_start, date__lte=check_date)
        m_income = float(m_qs.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0)
        m_savings = float(m_qs.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0)
        if m_income > 0 and (m_savings / m_income) * 100 >= target_rate:
            streak += 1
            check_date = m_start - timedelta(days=1)
        else:
            break

    if streak >= 2:
        insights.append({
            'type': 'success',
            'title': f"Série d'épargne: {streak} mois !",
            'message': f"Vous atteignez votre objectif d'épargne depuis {streak} mois consécutifs. Continuez !",
            'icon': '🔥',
            'data': {'streak': streak}
        })

    # 5. Biggest spending category this month
    if expenses > 0:
        top_cat = None
        top_amount = 0
        for cat in Category.objects.filter(user=user, type='expense'):
            spent = float(qs_month.filter(category=cat, type='expense').aggregate(t=Sum('amount'))['t'] or 0)
            if spent > top_amount:
                top_amount = spent
                top_cat = cat
        if top_cat:
            pct_of_expenses = (top_amount / expenses) * 100
            insights.append({
                'type': 'info',
                'title': 'Plus grande dépense du mois',
                'message': f"{top_cat.icon} {top_cat.name} représente {pct_of_expenses:.1f}% de vos dépenses ({top_amount:.0f}€)",
                'icon': '📊',
                'data': {'category': top_cat.name, 'amount': top_amount, 'pct': round(pct_of_expenses, 1)}
            })

    return insights
