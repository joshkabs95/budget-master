from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum


def get_savings_summary(user, month: str = None):
    from apps.transactions.models import Transaction
    from apps.savings.models import SavingsAccount, SavingsRule

    today = date.today()
    if month:
        year, m = month.split('-')
        first = date(int(year), int(m), 1)
    else:
        first = today.replace(day=1)

    if first.month == 12:
        last = date(first.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(first.year, first.month + 1, 1) - timedelta(days=1)

    txns = Transaction.objects.filter(user=user, date__range=[first, last])
    income = txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    saved = txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')

    savings_rate = float(saved / income * 100) if income > 0 else 0.0

    accounts = SavingsAccount.objects.filter(user=user)
    accounts_data = []
    for acc in accounts:
        acc_saved = txns.filter(type='saving', savings_account=acc).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        accounts_data.append({
            "id": acc.id,
            "name": acc.name,
            "icon": acc.icon,
            "color": acc.color,
            "balance": float(acc.balance),
            "target": float(acc.target) if acc.target else None,
            "interest_rate": float(acc.interest_rate) if acc.interest_rate else None,
            "month_contribution": float(acc_saved),
            "progress": float(acc_saved / acc.target * 100) if acc.target and acc.target > 0 else None,
        })

    try:
        rule = SavingsRule.objects.get(user=user, active=True)
        target = float(rule.savings_target)
    except SavingsRule.DoesNotExist:
        target = 20.0

    # 6-month average rate
    six_months_ago = today.replace(day=1)
    for _ in range(5):
        if six_months_ago.month == 1:
            six_months_ago = six_months_ago.replace(year=six_months_ago.year - 1, month=12)
        else:
            six_months_ago = six_months_ago.replace(month=six_months_ago.month - 1)

    old_txns = Transaction.objects.filter(user=user, date__gte=six_months_ago)
    old_income = old_txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    old_saved = old_txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    avg_rate_6m = float(old_saved / old_income * 100) if old_income > 0 else 0.0

    return {
        "month": first.strftime('%Y-%m'),
        "income": float(income),
        "saved": float(saved),
        "savings_rate": round(savings_rate, 1),
        "target_rate": target,
        "avg_rate_6m": round(avg_rate_6m, 1),
        "accounts": accounts_data,
        "total_balance": sum(a['balance'] for a in accounts_data),
    }
