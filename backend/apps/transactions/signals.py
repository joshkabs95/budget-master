import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
@receiver(post_delete, sender=Transaction)
def transaction_changed(sender, instance, **kwargs):
    """Déclenche le pipeline event-driven après chaque changement de transaction."""
    try:
        from apps.notifications.tasks import process_transaction_event
        process_transaction_event.delay(instance.user_id)
    except Exception:
        logger.exception('transaction_changed: impossible d\'envoyer la tâche Celery (user=%s)', instance.user_id)


@receiver(post_save, sender=Transaction)
def auto_link_goal(sender, instance, created, **kwargs):
    """
    Auto-link a goal when a transaction is created with no goal assigned.
    Uses QuerySet.update() to avoid triggering post_save recursion.
    """
    update_fields = kwargs.get('update_fields')
    if update_fields and 'goal' not in update_fields:
        return
    if instance.goal_id is not None:
        return

    try:
        from .services.goal_linker import find_best_goal
        goal = find_best_goal(instance)
        if goal is None:
            return
        # Bypass post_save to avoid infinite loop
        Transaction.objects.filter(pk=instance.pk).update(goal=goal)
        instance.goal_id = goal.pk
        instance.goal = goal
        # Credit the goal
        goal.current_amount += instance.amount
        goal.save(update_fields=['current_amount'])
    except Exception:
        logger.exception('auto_link_goal: erreur pour transaction pk=%s', instance.pk)


@receiver(post_delete, sender=Transaction)
def unlink_goal_on_delete(sender, instance, **kwargs):
    """Subtract transaction amount from its goal when the transaction is deleted."""
    if not instance.goal_id:
        return
    try:
        from apps.goals.models import Goal
        goal = Goal.objects.filter(pk=instance.goal_id).first()
        if goal:
            goal.current_amount = max(goal.current_amount - instance.amount, 0)
            goal.save(update_fields=['current_amount'])
    except Exception:
        logger.exception('unlink_goal_on_delete: erreur pour transaction pk=%s', instance.pk)
