"""
Celery tasks — Notification Service.

Flow (event-driven):
  transaction.saved  →  process_transaction_event.delay(user_id)
    → generate_insights()
    → create Notification objects for red/orange insights
    → send_email_notification.delay(id)  [only if EMAIL_HOST_USER configured]
"""
from celery import shared_task
from celery.schedules import crontab


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_transaction_event(self, user_id: int):
    """
    Triggered after any transaction create/update/delete.
    Runs insights + risk score and creates Notification records for new alerts.
    """
    try:
        from django.utils import timezone
        from apps.users.models import User
        from apps.transactions.services.insights import generate_insights
        from .models import Notification

        user = User.objects.get(id=user_id)
        insights = generate_insights(user)
        today = timezone.now().date()

        created_ids = []
        for insight in insights:
            severity = insight.get('severity', 'orange')
            if severity not in ('red', 'orange'):
                continue

            itype = insight.get('type', 'info')
            category = insight.get('category', '')
            # Deduplicate: one notification per (user, type, category) per day
            qs = Notification.objects.filter(user=user, type=itype, created_at__date=today)
            if category:
                qs = qs.filter(message__icontains=category)
            if qs.exists():
                continue

            notif = Notification.objects.create(
                user=user,
                type=itype,
                severity=severity,
                message=insight.get('message', ''),
            )
            created_ids.append(notif.id)

            # Send email for red alerts only
            if severity == 'red':
                send_email_notification.delay(notif.id)

        return {'created': len(created_ids), 'ids': created_ids}

    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def send_email_notification(self, notification_id: int):
    """Send an email for a given Notification (if SMTP is configured)."""
    try:
        from django.conf import settings
        from django.core.mail import send_mail
        from .models import Notification

        if not getattr(settings, 'EMAIL_HOST_USER', ''):
            return 'email_not_configured'

        notif = Notification.objects.select_related('user').get(id=notification_id)
        if notif.email_sent or not notif.user.email:
            return 'skipped'

        send_mail(
            subject=f'[Budget Master] ⚠️ {notif.get_type_display()}',
            message=notif.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notif.user.email],
            fail_silently=False,
        )
        notif.email_sent = True
        notif.save(update_fields=['email_sent'])
        return 'sent'

    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def spawn_recurring_transactions():
    """
    Tâche planifiée : 1er de chaque mois à 6h00.
    Crée les occurrences mensuelles/hebdo/annuelles manquantes.
    """
    try:
        from apps.transactions.services.auto_recurring import spawn_recurring_all_users
        summary = spawn_recurring_all_users()
        total = sum(summary.values())
        return {'created': total, 'by_user': summary}
    except Exception as exc:
        return {'error': str(exc)}


@shared_task
def daily_budget_check():
    """
    Tâche planifiée : chaque jour à 8h00.
    Vérifie les budgets dépassés / en alerte pour tous les utilisateurs actifs
    (= ayant au moins une transaction ce mois-ci).
    """
    try:
        from django.utils import timezone
        from apps.users.models import User
        from apps.transactions.models import Transaction
        from apps.transactions.services.insights import generate_insights
        from .models import Notification

        today = timezone.now().date()
        first_of_month = today.replace(day=1)

        active_user_ids = Transaction.objects.filter(
            date__gte=first_of_month
        ).values_list('user_id', flat=True).distinct()

        created_total = 0
        for user_id in active_user_ids:
            try:
                user = User.objects.get(id=user_id)
                insights = generate_insights(user)
                for insight in insights:
                    severity = insight.get('severity', 'orange')
                    if severity not in ('red', 'orange'):
                        continue
                    itype = insight.get('type', 'info')
                    category = insight.get('category', '')
                    qs = Notification.objects.filter(user=user, type=itype, created_at__date=today)
                    if category:
                        qs = qs.filter(message__icontains=category)
                    if qs.exists():
                        continue
                    notif = Notification.objects.create(
                        user=user, type=itype, severity=severity,
                        message=insight.get('message', ''),
                    )
                    created_total += 1
                    if severity == 'red':
                        send_email_notification.delay(notif.id)
            except Exception:
                continue

        return {'checked_users': len(active_user_ids), 'created': created_total}
    except Exception as exc:
        return {'error': str(exc)}


@shared_task
def monthly_recap():
    """
    Tâche planifiée : dernier jour du mois à 20h00.
    Envoie une notification récap mensuel à chaque utilisateur actif.
    """
    try:
        from django.utils import timezone
        from django.db.models import Sum
        from decimal import Decimal
        from apps.users.models import User
        from apps.transactions.models import Transaction
        from .models import Notification

        today = timezone.now().date()
        first_of_month = today.replace(day=1)

        active_user_ids = Transaction.objects.filter(
            date__gte=first_of_month
        ).values_list('user_id', flat=True).distinct()

        for user_id in active_user_ids:
            try:
                user = User.objects.get(id=user_id)
                txns = Transaction.objects.filter(user=user, date__gte=first_of_month)
                income   = txns.filter(type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
                expenses = txns.filter(type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
                savings  = txns.filter(type='saving').aggregate(s=Sum('amount'))['s'] or Decimal('0')
                balance  = income - expenses - savings

                rate = round(float(savings / income * 100), 1) if income > 0 else 0
                month_label = today.strftime('%B %Y')

                if balance >= 0:
                    severity = 'green'
                    emoji = '✅'
                elif balance > -200:
                    severity = 'orange'
                    emoji = '⚠️'
                else:
                    severity = 'red'
                    emoji = '🔴'

                message = (
                    f"{emoji} Récap {month_label} — "
                    f"Revenus {income:.0f}€ · Dépenses {expenses:.0f}€ · "
                    f"Épargne {savings:.0f}€ · Taux {rate}% · "
                    f"Solde {'+' if balance >= 0 else ''}{balance:.0f}€"
                )

                # One recap per user per month
                already = Notification.objects.filter(
                    user=user, type='info',
                    message__startswith=f"{'✅' if severity=='green' else emoji} Récap {month_label}",
                    created_at__date=today,
                ).exists()
                if not already:
                    Notification.objects.create(
                        user=user, type='info', severity=severity, message=message,
                    )
            except Exception:
                continue

        return {'notified': len(active_user_ids)}
    except Exception as exc:
        return {'error': str(exc)}
