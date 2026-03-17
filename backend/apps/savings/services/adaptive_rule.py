from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Avg


class AdaptiveRuleEngine:
    """
    Moteur de compensation intelligent de la règle 50/30/20.

    Hiérarchie de protection (immuable) :
      PRIORITÉ 1 — Épargne  (20%) : objectif sacré
      PRIORITÉ 2 — Besoins  (50%) : levier secondaire
      PRIORITÉ 3 — Envies   (30%) : premier levier toujours

    Règle fondamentale :
      Quand l'épargne est en danger, on réduit les envies
      en premier. Les besoins ne sont touchés qu'en dernier
      recours. On étale dans le temps plutôt que de brutaliser.
    """

    def compensate(self, rule, current_rates: dict) -> dict:
        """
        current_rates = {
          'savings': 14.0,
          'needs':   56.0,
          'wants':   30.0,
        }
        """
        savings_gap = float(rule.savings_target) - current_rates['savings']

        if savings_gap <= 0:
            return {
                "status": "green",
                "severity": "green",
                "plan": None,
                "current_rates": current_rates,
                "targets": {
                    "savings": float(rule.savings_target),
                    "needs": float(rule.needs_target),
                    "wants": float(rule.wants_target),
                }
            }

        plan = {"steps": [], "remaining_gap": savings_gap}
        gap = savings_gap

        # ÉTAPE 1 : Réduire les Envies
        wants_margin = current_rates['wants'] - float(rule.wants_floor)
        wants_cut = min(gap, max(0, wants_margin))
        gap -= wants_cut

        if wants_cut > 0:
            plan['steps'].append({
                "lever": "wants",
                "cut": round(wants_cut, 2),
                "new_target": round(current_rates['wants'] - wants_cut, 2),
            })

        # ÉTAPE 2 : Réduire les Besoins si nécessaire
        if gap > 0:
            needs_margin = current_rates['needs'] - float(rule.needs_floor)
            needs_cut = min(gap, max(0, needs_margin))
            gap -= needs_cut

            if needs_cut > 0:
                plan['steps'].append({
                    "lever": "needs",
                    "cut": round(needs_cut, 2),
                    "new_target": round(current_rates['needs'] - needs_cut, 2),
                    "warning": "Zone de vigilance — besoins compressés",
                })

        # ÉTAPE 3 : Gap résiduel = situation critique
        plan['uncoverable_gap'] = round(gap, 2)
        plan['severity'] = self._severity(plan['steps'], gap, savings_gap)
        plan['catchup_months'] = self._catchup_months(savings_gap, rule)
        plan['monthly_amounts'] = self._to_amounts(plan['steps'], rule)
        plan['suggestions'] = self._concrete_suggestions(plan['steps'], current_rates, rule)
        plan['savings_gap'] = round(savings_gap, 2)

        # Human-readable message
        plan['message'] = self._build_message(plan, savings_gap, gap, rule)

        return {
            "status": plan['severity'],
            "severity": plan['severity'],
            "plan": plan,
            "current_rates": current_rates,
            "targets": {
                "savings": float(rule.savings_target),
                "needs": float(rule.needs_target),
                "wants": float(rule.wants_target),
            }
        }

    def _severity(self, steps, residual_gap, total_gap):
        if residual_gap > 0:
            return 'critical'
        if any(s['lever'] == 'needs' for s in steps):
            return 'red'
        if total_gap > 5:
            return 'orange'
        return 'yellow'

    def _catchup_months(self, gap, rule):
        if gap <= 5:
            return 1
        if gap <= 10:
            return 2
        return min(3, rule.catchup_max_months)

    def _avg_income(self, user):
        from apps.transactions.models import Transaction
        today = date.today()
        months_back = 3
        cutoff = date(today.year, today.month, 1)
        for _ in range(months_back - 1):
            if cutoff.month == 1:
                cutoff = cutoff.replace(year=cutoff.year - 1, month=12)
            else:
                cutoff = cutoff.replace(month=cutoff.month - 1)

        avg = Transaction.objects.filter(
            user=user,
            type='income',
            date__gte=cutoff
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

        return float(avg) / months_back if avg else 3000.0

    def _to_amounts(self, steps, rule):
        income = self._avg_income(rule.user)
        result = []
        for s in steps:
            result.append({
                **s,
                "monthly_euros": round((s['cut'] / 100) * income, 2)
            })
        return result

    def _concrete_suggestions(self, steps, rates, rule):
        """
        Analyse les transactions réelles des 3 derniers mois dans le bucket 'wants'
        et identifie les postes les plus facilement compressibles.
        Retourne top 3 suggestions.
        """
        from apps.transactions.models import Transaction
        from apps.categories.models import Category
        from django.db.models import Sum

        wants_step = next((s for s in steps if s['lever'] == 'wants'), None)
        if not wants_step:
            return []

        today = date.today()
        cutoff = date(today.year, today.month, 1)
        for _ in range(2):
            if cutoff.month == 1:
                cutoff = cutoff.replace(year=cutoff.year - 1, month=12)
            else:
                cutoff = cutoff.replace(month=cutoff.month - 1)

        top_wants = (
            Transaction.objects.filter(
                user=rule.user,
                type='expense',
                category__rule_bucket='wants',
                date__gte=cutoff
            )
            .values('category__name', 'category__icon')
            .annotate(total=Sum('amount'))
            .order_by('-total')[:3]
        )

        suggestions = []
        for row in top_wants:
            monthly_avg = float(row['total']) / 3
            suggestions.append({
                "category": row['category__name'],
                "icon": row['category__icon'],
                "monthly_avg": round(monthly_avg, 2),
                "suggestion": f"Réduire {row['category__name']} de ~{monthly_avg * 0.2:.0f}€/mois",
            })
        return suggestions

    def _build_message(self, plan, total_gap, residual_gap, rule):
        severity = plan['severity']
        if severity == 'critical':
            return (
                "Ce n'est pas un problème de comportement, c'est un problème de charges fixes. "
                "Revoir loyer / abonnements ou augmenter les revenus."
            )
        if severity == 'red':
            return f"Épargne en danger (-{total_gap:.1f}%). Les Envies et Besoins doivent être réduits sur {plan['catchup_months']} mois."
        if severity == 'orange':
            return f"Tes Envies peuvent absorber -{total_gap:.1f}% pour ramener ton épargne à {rule.savings_target}% en {plan['catchup_months']} mois."
        return f"Petit écart d'épargne ({total_gap:.1f}%). Réduire légèrement les Envies suffit."
