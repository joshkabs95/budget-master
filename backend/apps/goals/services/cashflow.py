from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Avg


def project_cashflow(user, months: int = 24) -> list:
    """
    Project cash flow for the next `months` months.
    Includes:
    - Current balance (income - expenses - savings this month)
    - Recurring income detected (avg of last 3 months)
    - Recurring expenses detected
    - Goal expenses planned
    """
    from apps.transactions.models import Transaction
    from apps.goals.models import Goal

    today = date.today()

    # Detect recurring income (avg last 3 months)
    three_months_ago = today.replace(day=1)
    for _ in range(2):
        if three_months_ago.month == 1:
            three_months_ago = three_months_ago.replace(year=three_months_ago.year - 1, month=12)
        else:
            three_months_ago = three_months_ago.replace(month=three_months_ago.month - 1)

    past_txns = Transaction.objects.filter(user=user, date__gte=three_months_ago)
    avg_income = float(past_txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0) / 3
    avg_expenses = float(past_txns.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0) / 3
    avg_savings = float(past_txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0) / 3

    # Current balance (this month so far)
    first_of_month = today.replace(day=1)
    curr_txns = Transaction.objects.filter(user=user, date__gte=first_of_month)
    curr_income = float(curr_txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
    curr_expenses = float(curr_txns.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
    curr_savings = float(curr_txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)
    current_balance = curr_income - curr_expenses - curr_savings

    # Goals of type 'expense' with future deadlines
    expense_goals = Goal.objects.filter(
        user=user,
        type='expense',
        deadline__gte=today
    )

    projection = []
    running_balance = current_balance
    net_monthly = avg_income - avg_expenses - avg_savings

    for i in range(months):
        # Calculate month
        m = (today.month + i - 1) % 12 + 1
        y = today.year + (today.month + i - 1) // 12

        month_str = f"{y}-{m:02d}"
        month_start = date(y, m, 1)
        month_end = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)

        # Planned expenses from goals this month
        planned_expenses = []
        for goal in expense_goals:
            if month_start <= goal.deadline <= month_end:
                remaining = float(goal.target_amount - goal.current_amount)
                planned_expenses.append({
                    "goal_id": goal.id,
                    "goal_name": goal.name,
                    "goal_icon": goal.icon,
                    "amount": remaining,
                })

        total_planned = sum(e['amount'] for e in planned_expenses)
        running_balance += net_monthly - total_planned

        projection.append({
            "month": month_str,
            "projected_income": round(avg_income, 2),
            "projected_expenses": round(avg_expenses, 2),
            "projected_savings": round(avg_savings, 2),
            "net": round(net_monthly, 2),
            "planned_expenses": planned_expenses,
            "total_planned": round(total_planned, 2),
            "running_balance": round(running_balance, 2),
            "alert": running_balance < 0,
        })

    return projection
