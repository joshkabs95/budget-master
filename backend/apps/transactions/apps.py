from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    name = 'apps.transactions'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import apps.transactions.signals  # noqa: F401
