from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.categories.defaults import create_default_categories

class Command(BaseCommand):
    help = 'Crée les catégories par défaut pour tous les utilisateurs'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        total = 0
        for user in users:
            n = create_default_categories(user)
            if n:
                self.stdout.write(f'  {user.username} : +{n} catégories')
            total += n
        self.stdout.write(self.style.SUCCESS(f'\n✓ {total} catégories créées sur {users.count()} utilisateurs'))
