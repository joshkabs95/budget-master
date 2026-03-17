from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with test data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')

        # Clean existing test data
        User.objects.filter(email='test@test.com').delete()

        # Create user
        user = User.objects.create_user(
            email='test@test.com',
            username='testuser',
            password='test123',
            first_name='Jean',
            last_name='Dupont',
        )
        self.stdout.write(f'Created user: {user.email}')

        # Create categories
        from apps.categories.models import Category
        categories_data = [
            {'name': 'Alimentation', 'icon': '🛒', 'color': '#22c55e', 'type': 'expense', 'budget_limit': 600, 'rule_bucket': 'needs'},
            {'name': 'Loyer', 'icon': '🏠', 'color': '#3b82f6', 'type': 'expense', 'budget_limit': 900, 'rule_bucket': 'needs'},
            {'name': 'Transport', 'icon': '🚗', 'color': '#f97316', 'type': 'expense', 'budget_limit': 150, 'rule_bucket': 'needs'},
            {'name': 'Loisirs', 'icon': '🎮', 'color': '#a855f7', 'type': 'expense', 'budget_limit': 200, 'rule_bucket': 'wants'},
            {'name': 'Services', 'icon': '📱', 'color': '#06b6d4', 'type': 'expense', 'budget_limit': 100, 'rule_bucket': 'wants'},
            {'name': 'Revenus', 'icon': '💰', 'color': '#c9a84c', 'type': 'income', 'budget_limit': None, 'rule_bucket': 'savings'},
            {'name': 'Épargne', 'icon': '🏦', 'color': '#22c55e', 'type': 'expense', 'budget_limit': None, 'rule_bucket': 'savings'},
            {'name': 'Restaurants', 'icon': '🍽️', 'color': '#ef4444', 'type': 'expense', 'budget_limit': 150, 'rule_bucket': 'wants'},
            {'name': 'Santé', 'icon': '💊', 'color': '#10b981', 'type': 'expense', 'budget_limit': 100, 'rule_bucket': 'needs'},
        ]
        cats = {}
        for c in categories_data:
            budget_limit = Decimal(str(c['budget_limit'])) if c['budget_limit'] else None
            cat = Category.objects.create(
                user=user,
                name=c['name'],
                icon=c['icon'],
                color=c['color'],
                type=c['type'],
                budget_limit=budget_limit,
                rule_bucket=c['rule_bucket'],
            )
            cats[c['name']] = cat
        self.stdout.write(f'Created {len(cats)} categories')

        # Create savings accounts
        from apps.savings.models import SavingsAccount, SavingsRule
        livret_a = SavingsAccount.objects.create(
            user=user,
            name='Livret A',
            target=Decimal('10000'),
            interest_rate=Decimal('3.00'),
            color='#22c55e',
            icon='🏦',
        )
        pel = SavingsAccount.objects.create(
            user=user,
            name='PEL',
            target=Decimal('25000'),
            interest_rate=Decimal('2.25'),
            color='#3b82f6',
            icon='🏡',
        )
        self.stdout.write('Created savings accounts')

        # Create savings rule
        rule = SavingsRule.objects.create(
            user=user,
            savings_target=Decimal('20'),
            needs_target=Decimal('50'),
            wants_target=Decimal('30'),
            savings_tolerance=Decimal('5'),
            needs_tolerance=Decimal('5'),
            wants_tolerance=Decimal('5'),
            savings_floor=Decimal('15'),
            needs_floor=Decimal('40'),
            wants_floor=Decimal('10'),
            compensation_order=['wants', 'needs'],
            window_months=3,
            catchup_max_months=3,
            mode='adaptive',
            active=True,
        )
        self.stdout.write('Created savings rule')

        # Create transactions - 2 months of realistic data
        # Scenario: savings at ~14% this month (below 20% target)
        from apps.transactions.models import Transaction
        today = date.today()

        def get_month_start(months_ago):
            d = today.replace(day=1)
            for _ in range(months_ago):
                d = (d - timedelta(days=1)).replace(day=1)
            return d

        # Current month transactions
        m0 = get_month_start(0)
        # Last month transactions
        m1 = get_month_start(1)

        transactions_data = [
            # === CURRENT MONTH ===
            # Income: 2 salary transactions (~3200€/month)
            {'date': m0 + timedelta(days=1), 'amount': '3200.00', 'label': 'Salaire Janvier 2026', 'type': 'income', 'category': 'Revenus', 'savings_account': None},
            # Needs expenses
            {'date': m0 + timedelta(days=2), 'amount': '900.00', 'label': 'Loyer Janvier', 'type': 'expense', 'category': 'Loyer', 'savings_account': None},
            {'date': m0 + timedelta(days=3), 'amount': '142.50', 'label': 'Carrefour courses', 'type': 'expense', 'category': 'Alimentation', 'savings_account': None},
            {'date': m0 + timedelta(days=5), 'amount': '89.30', 'label': 'Carrefour Market', 'type': 'expense', 'category': 'Alimentation', 'savings_account': None},
            {'date': m0 + timedelta(days=6), 'amount': '65.00', 'label': 'SNCF billets', 'type': 'expense', 'category': 'Transport', 'savings_account': None},
            {'date': m0 + timedelta(days=7), 'amount': '45.90', 'label': 'EDF électricité', 'type': 'expense', 'category': 'Loyer', 'savings_account': None},
            {'date': m0 + timedelta(days=8), 'amount': '38.50', 'label': 'Lidl courses', 'type': 'expense', 'category': 'Alimentation', 'savings_account': None},
            # Wants expenses
            {'date': m0 + timedelta(days=4), 'amount': '14.99', 'label': 'Netflix abonnement', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m0 + timedelta(days=4), 'amount': '9.99', 'label': 'Spotify Premium', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m0 + timedelta(days=9), 'amount': '55.00', 'label': 'Restaurant Le Bistrot', 'type': 'expense', 'category': 'Restaurants', 'savings_account': None},
            {'date': m0 + timedelta(days=10), 'amount': '29.99', 'label': 'Amazon commande', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m0 + timedelta(days=11), 'amount': '24.99', 'label': 'SFR mobile', 'type': 'expense', 'category': 'Services', 'savings_account': None},
            {'date': m0 + timedelta(days=12), 'amount': '19.99', 'label': 'Free Internet', 'type': 'expense', 'category': 'Services', 'savings_account': None},
            # Savings: 14% of 3200 = 448€ (intentional gap to trigger compensation)
            {'date': m0 + timedelta(days=13), 'amount': '300.00', 'label': 'Virement Livret A', 'type': 'saving', 'category': 'Épargne', 'savings_account': 'livret_a'},
            {'date': m0 + timedelta(days=14), 'amount': '148.00', 'label': 'Virement PEL', 'type': 'saving', 'category': 'Épargne', 'savings_account': 'pel'},

            # === LAST MONTH ===
            # Income
            {'date': m1 + timedelta(days=1), 'amount': '3200.00', 'label': 'Salaire Décembre 2025', 'type': 'income', 'category': 'Revenus', 'savings_account': None},
            # Needs
            {'date': m1 + timedelta(days=2), 'amount': '900.00', 'label': 'Loyer Décembre', 'type': 'expense', 'category': 'Loyer', 'savings_account': None},
            {'date': m1 + timedelta(days=3), 'amount': '155.20', 'label': 'Auchan courses', 'type': 'expense', 'category': 'Alimentation', 'savings_account': None},
            {'date': m1 + timedelta(days=5), 'amount': '76.00', 'label': 'Monoprix', 'type': 'expense', 'category': 'Alimentation', 'savings_account': None},
            {'date': m1 + timedelta(days=6), 'amount': '85.00', 'label': 'Essence Total', 'type': 'expense', 'category': 'Transport', 'savings_account': None},
            {'date': m1 + timedelta(days=7), 'amount': '42.00', 'label': 'EDF décembre', 'type': 'expense', 'category': 'Loyer', 'savings_account': None},
            # Wants
            {'date': m1 + timedelta(days=4), 'amount': '14.99', 'label': 'Netflix abonnement', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m1 + timedelta(days=4), 'amount': '9.99', 'label': 'Spotify Premium', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m1 + timedelta(days=9), 'amount': '68.00', 'label': 'Restaurant fêtes', 'type': 'expense', 'category': 'Restaurants', 'savings_account': None},
            {'date': m1 + timedelta(days=10), 'amount': '45.00', 'label': 'FNAC cadeaux', 'type': 'expense', 'category': 'Loisirs', 'savings_account': None},
            {'date': m1 + timedelta(days=11), 'amount': '24.99', 'label': 'SFR mobile', 'type': 'expense', 'category': 'Services', 'savings_account': None},
            {'date': m1 + timedelta(days=12), 'amount': '19.99', 'label': 'Free Internet', 'type': 'expense', 'category': 'Services', 'savings_account': None},
            # Savings: also ~14% last month to establish pattern
            {'date': m1 + timedelta(days=13), 'amount': '300.00', 'label': 'Virement Livret A', 'type': 'saving', 'category': 'Épargne', 'savings_account': 'livret_a'},
            {'date': m1 + timedelta(days=14), 'amount': '150.00', 'label': 'Virement PEL', 'type': 'saving', 'category': 'Épargne', 'savings_account': 'pel'},
        ]

        account_map = {'livret_a': livret_a, 'pel': pel}

        for t in transactions_data:
            savings_acc = account_map.get(t['savings_account']) if t['savings_account'] else None
            cat = cats.get(t['category'])
            Transaction.objects.create(
                user=user,
                category=cat,
                savings_account=savings_acc,
                amount=Decimal(t['amount']),
                label=t['label'],
                date=t['date'],
                type=t['type'],
                source='manual',
            )

        self.stdout.write(f'Created {len(transactions_data)} transactions')

        # Create goals
        from apps.goals.models import Goal
        goals_data = [
            {
                'name': 'Réparation voiture',
                'type': 'expense',
                'target_amount': '800.00',
                'current_amount': '350.00',
                'deadline': today + timedelta(days=45),  # short (<90d)
                'icon': '🚗',
                'color': '#f97316',
                'savings_account': None,
            },
            {
                'name': 'Vacances été',
                'type': 'savings',
                'target_amount': '2500.00',
                'current_amount': '800.00',
                'deadline': today + timedelta(days=180),  # medium (3-12mo)
                'icon': '🏖️',
                'color': '#3b82f6',
                'savings_account': livret_a,
            },
            {
                'name': 'Apport immobilier',
                'type': 'savings',
                'target_amount': '50000.00',
                'current_amount': '8500.00',
                'deadline': today + timedelta(days=1095),  # long (>12mo, 3 years)
                'icon': '🏡',
                'color': '#a855f7',
                'savings_account': pel,
            },
            {
                'name': 'Formation professionnelle',
                'type': 'expense',
                'target_amount': '1500.00',
                'current_amount': '0.00',
                'deadline': today + timedelta(days=548),  # long (>12mo, 18 months)
                'icon': '📚',
                'color': '#22c55e',
                'savings_account': None,
            },
        ]

        for g in goals_data:
            Goal.objects.create(
                user=user,
                savings_account=g['savings_account'],
                name=g['name'],
                type=g['type'],
                target_amount=Decimal(g['target_amount']),
                current_amount=Decimal(g['current_amount']),
                deadline=g['deadline'],
                icon=g['icon'],
                color=g['color'],
            )
        self.stdout.write(f'Created {len(goals_data)} goals')

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed data created successfully!'
            f'\n  User: test@test.com / test123'
            f'\n  Savings accounts: Livret A, PEL'
            f'\n  Categories: {len(cats)}'
            f'\n  Transactions: {len(transactions_data)}'
            f'\n  Goals: {len(goals_data)}'
            f'\n  Note: Current savings rate ~14% (below 20% target → triggers compensation engine)'
        ))
