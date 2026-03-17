"""
Seed data command: creates realistic test data for 2 months.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed realistic test data for Budget Master'

    def handle(self, *args, **kwargs):
        from apps.categories.models import Category
        from apps.transactions.models import Transaction
        from apps.savings.models import SavingsAccount, SavingsRule
        from apps.goals.models import Goal

        self.stdout.write('🌱 Seeding data...')

        # Create user
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={'email': 'demo@budgetmaster.fr', 'locale': 'fr-FR', 'currency': 'EUR'}
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write('✅ User "demo" created (password: demo1234)')
        else:
            self.stdout.write('ℹ️  User "demo" already exists')

        # Clear existing data for demo user
        Transaction.objects.filter(user=user).delete()
        Category.objects.filter(user=user).delete()
        SavingsAccount.objects.filter(user=user).delete()
        SavingsRule.objects.filter(user=user).delete()
        Goal.objects.filter(user=user).delete()

        # Create categories
        categories = {
            'Alimentation': Category.objects.create(user=user, name='Alimentation', icon='🛒', color='#22c55e', type='expense', budget_limit=400, rule_bucket='needs'),
            'Logement':     Category.objects.create(user=user, name='Logement', icon='🏠', color='#3b82f6', type='expense', budget_limit=900, rule_bucket='needs'),
            'Transport':    Category.objects.create(user=user, name='Transport', icon='🚗', color='#f97316', type='expense', budget_limit=200, rule_bucket='needs'),
            'Loisirs':      Category.objects.create(user=user, name='Loisirs', icon='🎬', color='#a855f7', type='expense', budget_limit=150, rule_bucket='wants'),
            'Restaurants':  Category.objects.create(user=user, name='Restaurants', icon='🍽️', color='#ec4899', type='expense', budget_limit=120, rule_bucket='wants'),
            'Shopping':     Category.objects.create(user=user, name='Shopping', icon='🛍️', color='#8b5cf6', type='expense', budget_limit=100, rule_bucket='wants'),
            'Services':     Category.objects.create(user=user, name='Services', icon='📱', color='#6b6b7e', type='expense', budget_limit=80, rule_bucket='needs'),
            'Salaire':      Category.objects.create(user=user, name='Salaire', icon='💰', color='#22c55e', type='income', rule_bucket='needs'),
        }
        self.stdout.write('✅ Categories created')

        # Create savings accounts
        livret_a = SavingsAccount.objects.create(
            user=user, name='Livret A', icon='🏦', color='#3b82f6',
            balance=0, target=22950, interest_rate=3.0
        )
        pel = SavingsAccount.objects.create(
            user=user, name='PEL', icon='🏡', color='#22c55e',
            balance=0, target=61200, interest_rate=2.0
        )
        self.stdout.write('✅ Savings accounts created')

        # Create savings rule (adaptive, 20% target)
        rule = SavingsRule.objects.create(
            user=user,
            savings_target=20, needs_target=50, wants_target=30,
            savings_tolerance=5, needs_tolerance=5, wants_tolerance=5,
            savings_floor=15, needs_floor=40, wants_floor=10,
            compensation_order=['wants', 'needs'],
            window_months=3, catchup_max_months=3,
            mode='adaptive', active=True,
        )
        self.stdout.write('✅ Savings rule created')

        # Create goals
        today = date.today()
        goals_data = [
            # Court terme < 3 mois
            {'name': 'Vacances été', 'type': 'expense', 'target_amount': 800, 'current_amount': 200,
             'deadline': today + timedelta(days=60), 'icon': '🏖️', 'color': '#f97316'},
            # Moyen terme 3-12 mois
            {'name': 'Nouveau laptop', 'type': 'expense', 'target_amount': 1500, 'current_amount': 450,
             'deadline': today + timedelta(days=200), 'icon': '💻', 'color': '#3b82f6'},
            # Long terme > 12 mois
            {'name': 'Apport immobilier', 'type': 'savings', 'target_amount': 30000, 'current_amount': 5200,
             'deadline': today + timedelta(days=730), 'icon': '🏠', 'color': '#a855f7',
             'savings_account': livret_a},
            {'name': 'Tour du monde', 'type': 'savings', 'target_amount': 12000, 'current_amount': 1800,
             'deadline': today + timedelta(days=540), 'icon': '✈️', 'color': '#c9a84c'},
        ]
        for g in goals_data:
            sa = g.pop('savings_account', None)
            Goal.objects.create(user=user, savings_account=sa, **g)
        self.stdout.write('✅ Goals created')

        # Generate 2 months of transactions (intentional: savings at ~14%)
        transactions_data = self._build_transactions(categories, livret_a, pel, today)
        for t in transactions_data:
            Transaction.objects.create(user=user, **t)

        # Recalculate savings account balances
        livret_a.recalculate_balance()
        pel.recalculate_balance()

        self.stdout.write(f'✅ {len(transactions_data)} transactions created')
        self.stdout.write('')
        self.stdout.write('🎉 Seed complete! Login: demo / demo1234')
        self.stdout.write('📊 Intentional scenario: savings ~14% → compensation plan should trigger')

    def _build_transactions(self, cats, livret_a, pel, today):
        txns = []

        for months_ago in [1, 0]:
            y = today.year
            m = today.month - months_ago
            if m <= 0:
                m += 12
                y -= 1

            income = 3200  # Monthly salary
            # Intentionally savings = 14% of income = 448€
            # needs = 56%, wants = 30%

            # INCOME
            txns.append({
                'category': cats['Salaire'], 'savings_account': None,
                'amount': Decimal(str(income)), 'label': 'Virement salaire - Entreprise SAS',
                'date': date(y, m, 5), 'type': 'income', 'source': 'manual',
            })

            # NEEDS (56% = 1792€)
            txns += [
                {'category': cats['Logement'], 'savings_account': None,
                 'amount': Decimal('850'), 'label': 'Loyer appartement',
                 'date': date(y, m, 1), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Logement'], 'savings_account': None,
                 'amount': Decimal('45'), 'label': 'EDF - Facture électricité',
                 'date': date(y, m, 8), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Transport'], 'savings_account': None,
                 'amount': Decimal('84.10'), 'label': 'RATP - Navigo mensuel',
                 'date': date(y, m, 3), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Transport'], 'savings_account': None,
                 'amount': Decimal('60'), 'label': 'Total - Essence',
                 'date': date(y, m, 15), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Alimentation'], 'savings_account': None,
                 'amount': Decimal('180'), 'label': 'Carrefour - Courses hebdo',
                 'date': date(y, m, 7), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Alimentation'], 'savings_account': None,
                 'amount': Decimal('165'), 'label': 'Leclerc - Courses',
                 'date': date(y, m, 21), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Services'], 'savings_account': None,
                 'amount': Decimal('29.99'), 'label': 'Free - Abonnement mobile',
                 'date': date(y, m, 10), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Services'], 'savings_account': None,
                 'amount': Decimal('40'), 'label': 'Mutuelle santé',
                 'date': date(y, m, 5), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Alimentation'], 'savings_account': None,
                 'amount': Decimal('42'), 'label': 'Monoprix - Courses express',
                 'date': date(y, m, 25), 'type': 'expense', 'source': 'manual'},
            ]

            # WANTS (30% = 960€)
            txns += [
                {'category': cats['Restaurants'], 'savings_account': None,
                 'amount': Decimal('65'), 'label': 'Restaurant La Table',
                 'date': date(y, m, 12), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Restaurants'], 'savings_account': None,
                 'amount': Decimal('28.50'), 'label': 'Uber Eats - Sushi',
                 'date': date(y, m, 18), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Loisirs'], 'savings_account': None,
                 'amount': Decimal('17.99'), 'label': 'Netflix - Abonnement',
                 'date': date(y, m, 5), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Loisirs'], 'savings_account': None,
                 'amount': Decimal('9.99'), 'label': 'Spotify Premium',
                 'date': date(y, m, 5), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Loisirs'], 'savings_account': None,
                 'amount': Decimal('24'), 'label': 'Cinéma UGC - 2 places',
                 'date': date(y, m, 20), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Shopping'], 'savings_account': None,
                 'amount': Decimal('89'), 'label': 'FNAC - Livre + accessoires',
                 'date': date(y, m, 16), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Shopping'], 'savings_account': None,
                 'amount': Decimal('120'), 'label': 'Amazon - Commande diverse',
                 'date': date(y, m, 22), 'type': 'expense', 'source': 'manual'},
                {'category': cats['Restaurants'], 'savings_account': None,
                 'amount': Decimal('45'), 'label': 'Deliveroo - Pizza',
                 'date': date(y, m, 27), 'type': 'expense', 'source': 'manual'},
            ]

            # SAVINGS (14% = 448€) — intentionally below 20% target
            saving_amount_livret = Decimal('300')
            saving_amount_pel = Decimal('148')

            txns.append({
                'category': None, 'savings_account': livret_a,
                'amount': saving_amount_livret,
                'label': 'Virement épargne - Livret A',
                'date': date(y, m, 28), 'type': 'saving', 'source': 'manual',
            })
            txns.append({
                'category': None, 'savings_account': pel,
                'amount': saving_amount_pel,
                'label': 'Virement épargne - PEL',
                'date': date(y, m, 28), 'type': 'saving', 'source': 'manual',
            })
            txns.append({
                'category': None, 'savings_account': livret_a,
                'amount': Decimal('0'), 'label': '',  # will be skipped
                'date': date(y, m, 28), 'type': 'saving', 'source': 'manual',
            })
            # Remove the 0 one
            txns = [t for t in txns if t['amount'] > 0]

        return txns
