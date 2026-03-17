"""
ForecastEngine — projection financière avec moyenne pondérée et tendance.

Poids par défaut : [0.5, 0.3, 0.2] → M-1 pèse le plus.
Score de confiance : 1 - (std / mean). Proche de 1 = données stables.
"""
import statistics
from datetime import date
from django.db.models import Sum
from django.core.cache import cache


class ForecastEngine:
    WEIGHTS = [0.5, 0.3, 0.2]   # M-1, M-2, M-3
    CACHE_TIMEOUT = 3600 * 6    # 6 h

    def __init__(self, user):
        self.user = user

    # ── Data ──────────────────────────────────────────────────────────────────

    def monthly_history(self, months_back: int = 6) -> list:
        """[M-1, M-2, ..., M-n] — le plus récent en premier."""
        cache_key = f'forecast_history_{self.user.id}_{months_back}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from apps.transactions.models import Transaction

        today = date.today()
        result = []

        for i in range(1, months_back + 1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12; y -= 1
            month_str = f'{y}-{m:02d}'

            qs = Transaction.objects.filter(user=self.user, date__year=y, date__month=m)
            income   = float(qs.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
            expenses = float(qs.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
            savings  = float(qs.filter(type='saving').aggregate(s=Sum('amount'))['s'] or 0)
            result.append({'month': month_str, 'income': income,
                           'expenses': expenses, 'savings': savings,
                           'net': income - expenses - savings})

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    # ── Statistics ────────────────────────────────────────────────────────────

    def weighted_avg(self, values: list) -> float:
        """Moyenne pondérée des 3 valeurs les plus récentes."""
        if not values:
            return 0.0
        w = self.WEIGHTS
        n = min(len(values), len(w))
        total_w = sum(w[:n])
        return sum(w[i] * values[i] for i in range(n)) / total_w

    def linear_trend(self, values: list) -> float:
        """Pente de la régression linéaire (€/mois). values[0]=M-1."""
        if len(values) < 2:
            return 0.0
        chron = list(reversed(values))
        n = len(chron)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(chron)
        num   = sum((i - x_mean) * (chron[i] - y_mean) for i in range(n))
        denom = sum((i - x_mean) ** 2 for i in range(n))
        return num / denom if denom else 0.0

    def confidence_score(self, values: list) -> float:
        """1 - (std / mean). 1 = stable, 0 = très variable."""
        if len(values) < 2:
            return 0.5
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        return round(max(0.0, min(1.0, 1 - statistics.stdev(values) / mean)), 3)

    def calibrate_weights(self, estimated: float, real: float) -> list:
        """Ajuste les poids si l'estimation était trop loin du réel."""
        if estimated == 0:
            return list(self.WEIGHTS)
        ratio = real / estimated
        w = list(self.WEIGHTS)
        if ratio > 1.1:
            w[0] = min(0.7, w[0] + 0.05)
        elif ratio < 0.9:
            w[0] = max(0.3, w[0] - 0.05)
        total = sum(w)
        return [round(x / total, 4) for x in w]

    # ── Projection ────────────────────────────────────────────────────────────

    def project(self, months: int = 6) -> list:
        """Retourne `months` mois de projection à partir du mois prochain."""
        history = self.monthly_history(6)
        incomes  = [h['income']   for h in history]
        expenses = [h['expenses'] for h in history]
        savings  = [h['savings']  for h in history]

        proj_income   = self.weighted_avg(incomes)
        proj_expenses = self.weighted_avg(expenses)
        proj_savings  = self.weighted_avg(savings)
        trend         = self.linear_trend(expenses)

        conf = round(
            (self.confidence_score(incomes) + self.confidence_score(expenses) + self.confidence_score(savings)) / 3,
            3)

        today = date.today()
        result = []
        for i in range(months):
            y, m = today.year, today.month + 1 + i
            while m > 12:
                m -= 12; y += 1
            month_expenses = max(0.0, proj_expenses + trend * (i + 1))
            net = proj_income - month_expenses - proj_savings
            result.append({
                'month': f'{y}-{m:02d}',
                'is_forecast': True,
                'projected_income':   round(proj_income, 2),
                'projected_expenses': round(month_expenses, 2),
                'projected_savings':  round(proj_savings, 2),
                'net': round(net, 2),
                'confidence': conf,
                'trend_expenses': round(trend, 2),
            })
        return result
