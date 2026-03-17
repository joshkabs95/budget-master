from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction


@receiver(post_save, sender=Transaction)
def update_savings_balance_on_save(sender, instance, **kwargs):
    if instance.type == 'saving' and instance.savings_account:
        instance.savings_account.recalculate_balance()


@receiver(post_delete, sender=Transaction)
def update_savings_balance_on_delete(sender, instance, **kwargs):
    if instance.type == 'saving' and instance.savings_account:
        instance.savings_account.recalculate_balance()
