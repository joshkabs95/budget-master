class AdaptiveRuleEngine:
    def compensate(self, rule, current_rates):
        savings_gap = float(rule.savings_target) - current_rates['savings']
        if savings_gap <= 0:
            return {"status": "green", "plan": None}

        plan = {"steps": [], "remaining_gap": savings_gap}
        gap = savings_gap

        # Step 1: cut wants first
        wants_margin = current_rates['wants'] - float(rule.wants_floor)
        wants_cut = min(gap, max(0, wants_margin))
        gap -= wants_cut
        if wants_cut > 0:
            plan['steps'].append({
                "lever": "wants",
                "cut": wants_cut,
                "new_target": current_rates['wants'] - wants_cut
            })

        # Step 2: cut needs if needed
        if gap > 0:
            needs_margin = current_rates['needs'] - float(rule.needs_floor)
            needs_cut = min(gap, max(0, needs_margin))
            gap -= needs_cut
            if needs_cut > 0:
                plan['steps'].append({
                    "lever": "needs",
                    "cut": needs_cut,
                    "new_target": current_rates['needs'] - needs_cut,
                    "warning": "Zone de vigilance — besoins compressés"
                })

        plan['uncoverable_gap'] = gap
        plan['severity'] = self._severity(plan['steps'], gap, savings_gap)
        plan['catchup_months'] = self._catchup_months(savings_gap, rule)
        plan['remaining_gap'] = gap
        plan['monthly_amounts'] = self._to_amounts(plan['steps'], rule)
        plan['suggestions'] = self._concrete_suggestions(plan['steps'], current_rates, rule)
        return {"status": plan['severity'], "plan": plan}

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

    def _to_amounts(self, steps, rule):
        income = self._avg_income(rule.user)
        return [{**s, "monthly_euros": round((s['cut'] / 100) * income, 2)} for s in steps]

    def _avg_income(self, user):
        from apps.transactions.models import Transaction
        from django.db.models import Sum
        from datetime import date, timedelta

        totals = []
        d = date.today().replace(day=1)
        for i in range(3):
            if i > 0:
                d = (d - timedelta(days=1)).replace(day=1)
            from calendar import monthrange
            last_day = monthrange(d.year, d.month)[1]
            m_end = d.replace(day=last_day)
            month_income = float(
                Transaction.objects.filter(
                    user=user, type='income', date__gte=d, date__lte=m_end
                ).aggregate(total=Sum('amount'))['total'] or 0
            )
            totals.append(month_income)

        return sum(totals) / max(len(totals), 1) if totals else 3000

    def _concrete_suggestions(self, steps, rates, rule):
        from apps.transactions.models import Transaction
        from django.db.models import Sum
        from datetime import date, timedelta

        suggestions = []
        wants_step = next((s for s in steps if s['lever'] == 'wants'), None)
        if wants_step:
            d = date.today().replace(day=1)
            all_cats = {}
            for i in range(3):
                if i > 0:
                    d = (d - timedelta(days=1)).replace(day=1)
                from calendar import monthrange
                last_day = monthrange(d.year, d.month)[1]
                m_end = d.replace(day=last_day)
                txns = Transaction.objects.filter(
                    user=rule.user,
                    category__rule_bucket='wants',
                    date__gte=d,
                    date__lte=m_end
                ).values('category__name').annotate(total=Sum('amount'))
                for t in txns:
                    name = t['category__name']
                    all_cats[name] = all_cats.get(name, 0) + float(t['total'])

            top_cats = sorted(all_cats.items(), key=lambda x: x[1], reverse=True)[:3]
            for name, total in top_cats:
                avg = total / 3
                suggestions.append({
                    "category": name,
                    "avg_monthly": round(avg, 2),
                    "suggestion": f"Réduire {name} de {avg * 0.3:.0f}€/mois"
                })

        return suggestions[:3]

    def get_current_rates(self, user, window_months=3):
        """Calculate current spending rates for the last N months."""
        from apps.transactions.models import Transaction
        from apps.categories.models import Category
        from django.db.models import Sum
        from datetime import date, timedelta

        now = date.today()
        d = now.replace(day=1)
        for _ in range(window_months - 1):
            d = (d - timedelta(days=1)).replace(day=1)

        transactions = Transaction.objects.filter(user=user, date__gte=d)

        total_income = float(transactions.filter(type='income').aggregate(
            total=Sum('amount'))['total'] or 0)

        if total_income == 0:
            return {'savings': 0, 'needs': 0, 'wants': 0, 'total_income': 0}

        def get_bucket_total(bucket):
            cat_ids = Category.objects.filter(user=user, rule_bucket=bucket).values_list('id', flat=True)
            return float(transactions.filter(
                type='expense',
                category_id__in=cat_ids
            ).aggregate(total=Sum('amount'))['total'] or 0)

        savings_total = float(transactions.filter(type='saving').aggregate(
            total=Sum('amount'))['total'] or 0)
        needs_total = get_bucket_total('needs')
        wants_total = get_bucket_total('wants')

        return {
            'savings': round((savings_total / total_income) * 100, 2),
            'needs': round((needs_total / total_income) * 100, 2),
            'wants': round((wants_total / total_income) * 100, 2),
            'total_income': total_income,
            'savings_amount': savings_total,
            'needs_amount': needs_total,
            'wants_amount': wants_total,
        }
