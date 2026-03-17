from django.db.models import Sum, Avg
from datetime import date, timedelta
import calendar


def project_cashflow(user, months=24):
    """Project 24-month cash flow based on recurring income/expenses and goals."""
    from apps.transactions.models import Transaction
    from apps.savings.models import SavingsAccount
    from apps.goals.models import Goal

    now = date.today()

    # Get current total savings balance
    accounts = SavingsAccount.objects.filter(user=user)
    current_balance = sum(float(a.balance) for a in accounts)

    # Detect recurring income (avg of last 3 months)
    monthly_income = _get_avg_monthly(user, 'income', 3)
    monthly_expenses = _get_avg_monthly(user, 'expense', 3)
    monthly_savings = _get_avg_monthly(user, 'saving', 3)

    net_monthly = monthly_income - monthly_expenses - monthly_savings

    # Get all goals
    goals = Goal.objects.filter(user=user)

    cashflow = []
    running_balance = current_balance

    for i in range(months):
        m_offset = now.month + i
        year = now.year + (m_offset - 1) // 12
        month = ((m_offset - 1) % 12) + 1
        month_date = date(year, month, 1)

        # Goals due this month
        month_goals = []
        goal_impact = 0
        for goal in goals:
            if goal.deadline.year == year and goal.deadline.month == month:
                if goal.type == 'expense':
                    remaining = max(0, float(goal.target_amount) - float(goal.current_amount))
                    goal_impact -= remaining
                    month_goals.append({
                        'id': goal.id,
                        'name': goal.name,
                        'icon': goal.icon,
                        'color': goal.color,
                        'amount': -remaining,
                        'type': goal.type,
                    })
                else:
                    month_goals.append({
                        'id': goal.id,
                        'name': goal.name,
                        'icon': goal.icon,
                        'color': goal.color,
                        'amount': float(goal.target_amount),
                        'type': goal.type,
                    })

        # Add monthly net + goal impact
        month_net = net_monthly + goal_impact
        running_balance += month_net + monthly_savings  # savings add to balance

        cashflow.append({
            'month': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%b %Y'),
            'income': monthly_income,
            'expenses': monthly_expenses,
            'savings': monthly_savings,
            'net': month_net,
            'balance': running_balance,
            'negative': running_balance < 0,
            'goals': month_goals,
            'goal_impact': goal_impact,
        })

    return cashflow


def _get_avg_monthly(user, t_type, months=3):
    """Get average monthly amount for transaction type over last N months."""
    from apps.transactions.models import Transaction

    now = date.today()
    totals = []

    for i in range(months):
        d = now.replace(day=1)
        for _ in range(i):
            d = (d - timedelta(days=1)).replace(day=1)

        last_day = calendar.monthrange(d.year, d.month)[1]
        m_end = d.replace(day=last_day)

        total = float(
            Transaction.objects.filter(
                user=user,
                type=t_type,
                date__gte=d,
                date__lte=m_end
            ).aggregate(t=Sum('amount'))['t'] or 0
        )
        totals.append(total)

    return sum(totals) / len(totals) if totals else 0
