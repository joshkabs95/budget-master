from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from .defaults import create_default_categories
        create_default_categories(instance)
    except Exception:
        pass  # fail silently — ne pas bloquer la création de l'user
