"""
BudgetProjector — projection de la règle 50/30/20.

Détecte les dépenses fixes (CV < 5%) vs variables.
Calcule le surplus résiduel et l'état de l'épargne projetée.
"""
import statistics
from datetime import date
from django.db.models import Sum


class BudgetProjector:
    FIXED_CV_THRESHOLD = 0.05
    SEVERITY_ORDER = ['green', 'yellow', 'orange', 'red', 'critical']

    def __init__(self, user, engine):
        self.user = user
        self.engine = engine

    def _category_history(self, months_back: int = 3) -> dict:
        from apps.transactions.models import Transaction
        today = date.today()
        result = {}
        for i in range(1, months_back + 1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12; y -= 1
            qs = (
                Transaction.objects.filter(user=self.user, type='expense', date__year=y, date__month=m)
                .values('category__id', 'category__name', 'category__icon', 'category__rule_bucket')
                .annotate(total=Sum('amount'))
            )
            for row in qs:
                cid = row['category__id']
                if cid not in result:
                    result[cid] = {
                        'name': row['category__name'],
                        'icon': row['category__icon'],
                        'bucket': row['category__rule_bucket'] or 'wants',
                        'monthly_totals': [],
                    }
                result[cid]['monthly_totals'].append(float(row['total'] or 0))
        return result

    def detect_fixed_costs(self) -> dict:
        cats = self._category_history(3)
        for cid, c in cats.items():
            totals = c['monthly_totals']
            if len(totals) < 2:
                c.update(is_fixed=False, cv=1.0, avg=totals[0] if totals else 0.0)
            else:
                mean = statistics.mean(totals)
                std  = statistics.stdev(totals)
                cv   = (std / mean) if mean > 0 else 1.0
                c.update(is_fixed=cv < self.FIXED_CV_THRESHOLD, cv=round(cv, 4), avg=round(mean, 2))
        return cats

    def _surplus_state(self, income, savings, savings_target_pct):
        if income == 0:
            return 'deficit'
        pct = savings / income * 100
        if pct >= savings_target_pct:
            return 'over_saving' if pct > savings_target_pct + 5 else 'on_target'
        return 'partial_savings' if pct >= savings_target_pct * 0.5 else 'deficit'

    def project_buckets(self, months: int = 6) -> dict:
        from apps.savings.models import SavingsRule
        projections = self.engine.project(months)
        cats = self.detect_fixed_costs()
        rule = SavingsRule.objects.filter(user=self.user, active=True).first()
        savings_target_pct = float(rule.savings_target) if rule else 20.0

        # Bucket ratios from historical category data
        needs_total = sum(c['avg'] for c in cats.values() if c.get('bucket') == 'needs')
        wants_total = sum(c['avg'] for c in cats.values() if c.get('bucket') == 'wants')
        bucket_total = (needs_total + wants_total) or 1.0
        needs_ratio = needs_total / bucket_total
        wants_ratio = wants_total / bucket_total

        month_projections = []
        worst = 'green'

        for p in projections:
            income  = p['projected_income']
            savings = p['projected_savings']
            total_expenses = p['projected_expenses']

            proj_needs = round(total_expenses * needs_ratio, 2)
            proj_wants = round(total_expenses * wants_ratio, 2)
            residual   = round(income - proj_needs - proj_wants - savings, 2)
            state      = self._surplus_state(income, savings, savings_target_pct)

            sev_map = {'on_target': 'green', 'over_saving': 'green',
                       'partial_savings': 'orange', 'deficit': 'red'}
            severity = sev_map.get(state, 'green')
            if self.SEVERITY_ORDER.index(severity) > self.SEVERITY_ORDER.index(worst):
                worst = severity

            month_projections.append({
                'month': p['month'],
                'is_forecast': True,
                'income':   income,
                'needs':    proj_needs,
                'wants':    proj_wants,
                'savings':  savings,
                'residual_surplus': residual,
                'surplus_state': state,
                'severity': severity,
                'confidence': p['confidence'],
                'needs_pct':   round(proj_needs / income * 100 if income else 0, 1),
                'wants_pct':   round(proj_wants / income * 100 if income else 0, 1),
                'savings_pct': round(savings  / income * 100 if income else 0, 1),
            })

        fixed_list    = sorted([{'name': c['name'], 'icon': c['icon'], 'bucket': c['bucket'], 'avg': c['avg']}
                                 for c in cats.values() if c.get('is_fixed')],  key=lambda x: -x['avg'])
        variable_list = sorted([{'name': c['name'], 'icon': c['icon'], 'bucket': c['bucket'], 'avg': c['avg'], 'cv': c['cv']}
                                 for c in cats.values() if not c.get('is_fixed')], key=lambda x: -x['avg'])

        return {
            'months': month_projections,
            'fixed_costs': fixed_list,
            'variable_costs': variable_list,
            'worst_forecast_alert': worst,
            'residual_surplus': month_projections[-1]['residual_surplus'] if month_projections else 0.0,
        }
