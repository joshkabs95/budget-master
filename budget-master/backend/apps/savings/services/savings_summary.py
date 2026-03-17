from django.db.models import Sum
from datetime import date, timedelta
import calendar


def get_monthly_savings_summary(user, months=12):
    """Get monthly savings summary for the last N months."""
    from apps.transactions.models import Transaction
    from apps.savings.models import SavingsAccount

    now = date.today()
    summary = []

    for i in range(months - 1, -1, -1):
        # Calculate month
        d = now.replace(day=1)
        for _ in range(i):
            d = (d - timedelta(days=1)).replace(day=1)

        m_start = d
        last_day = calendar.monthrange(d.year, d.month)[1]
        m_end = d.replace(day=last_day)

        qs = Transaction.objects.filter(user=user, date__gte=m_start, date__lte=m_end)
        income = float(qs.filter(type='income').aggregate(t=Sum('amount'))['t'] or 0)
        savings = float(qs.filter(type='saving').aggregate(t=Sum('amount'))['t'] or 0)

        rate = (savings / income * 100) if income > 0 else 0

        summary.append({
            'month': m_start.strftime('%Y-%m'),
            'label': m_start.strftime('%b %Y'),
            'income': income,
            'savings': savings,
            'rate': round(rate, 1),
        })

    return summary


def get_heatmap_data(user, months=12):
    """Get savings heatmap data - daily savings for last N months."""
    from apps.transactions.models import Transaction

    now = date.today()
    heatmap = []

    start = now.replace(day=1)
    for _ in range(months - 1):
        start = (start - timedelta(days=1)).replace(day=1)

    transactions = Transaction.objects.filter(
        user=user,
        type='saving',
        date__gte=start,
        date__lte=now
    ).values('date').annotate(total=Sum('amount')).order_by('date')

    day_map = {str(t['date']): float(t['total']) for t in transactions}

    # Fill all days
    current = start
    while current <= now:
        heatmap.append({
            'date': str(current),
            'amount': day_map.get(str(current), 0),
        })
        current += timedelta(days=1)

    return heatmap
