"""
Création automatique des transactions récurrentes.

- Parcourt toutes les transactions marquées is_recurring=True
- Pour chaque recurrence (monthly/weekly/yearly), crée la prochaine
  occurrence si elle n'existe pas encore pour la période courante
- Utilisé par la tâche Celery scheduled (1er de chaque mois à 6h)
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from apps.transactions.models import Transaction


def _next_date(ref_date: date, recurrence: str) -> date:
    if recurrence == 'monthly':
        return ref_date + relativedelta(months=1)
    if recurrence == 'weekly':
        return ref_date + timedelta(weeks=1)
    if recurrence == 'yearly':
        return ref_date + relativedelta(years=1)
    return ref_date + relativedelta(months=1)


def _period_start(d: date, recurrence: str) -> date:
    if recurrence == 'monthly':
        return d.replace(day=1)
    if recurrence == 'weekly':
        return d - timedelta(days=d.weekday())
    if recurrence == 'yearly':
        return d.replace(month=1, day=1)
    return d.replace(day=1)


def spawn_recurring_for_user(user) -> list:
    """
    Génère les occurrences manquantes pour la période en cours.
    Retourne la liste des transactions créées.
    """
    today = date.today()
    created = []

    templates = Transaction.objects.filter(
        user=user,
        is_recurring=True,
        recurrence__in=['monthly', 'weekly', 'yearly'],
    ).select_related('category', 'savings_account')

    for tpl in templates:
        period_start = _period_start(today, tpl.recurrence)
        period_end = _next_date(period_start, tpl.recurrence) - timedelta(days=1)

        # Déjà une occurrence dans la période courante ?
        exists = Transaction.objects.filter(
            user=user,
            label=tpl.label,
            amount=tpl.amount,
            type=tpl.type,
            date__range=(period_start, period_end),
            is_recurring=True,
        ).exclude(pk=tpl.pk).exists()

        if not exists and tpl.date < period_start:
            # Calcule la date de la prochaine occurrence dans la période
            occurrence_date = tpl.date
            while occurrence_date < period_start:
                occurrence_date = _next_date(occurrence_date, tpl.recurrence)

            if period_start <= occurrence_date <= period_end:
                new_tx = Transaction.objects.create(
                    user=user,
                    label=tpl.label,
                    amount=tpl.amount,
                    type=tpl.type,
                    date=occurrence_date,
                    category=tpl.category,
                    savings_account=tpl.savings_account,
                    is_recurring=True,
                    recurrence=tpl.recurrence,
                    notes=f'Générée automatiquement depuis #{tpl.pk}',
                    source='manual',
                )
                created.append(new_tx)

    return created


def spawn_recurring_all_users() -> dict:
    """Lance spawn_recurring_for_user pour tous les utilisateurs."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    summary = {}
    for user in User.objects.all():
        txns = spawn_recurring_for_user(user)
        if txns:
            summary[user.username] = len(txns)
    return summary
