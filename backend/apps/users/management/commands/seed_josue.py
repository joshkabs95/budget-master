"""
Management command : seed les données de Josue pour mars 2026.
Usage : python manage.py seed_josue [--reset]
"""
from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


# ── Catégories ────────────────────────────────────────────────────────────────

CATEGORIES = [
    # (nom, bucket, icône, type, budget_limit)
    ('Logement',       'needs',   '🏠', 'expense', Decimal('719.00')),
    ('Énergie',        'needs',   '⚡', 'expense', Decimal('70.00')),
    ('Crédit',         'needs',   '💳', 'expense', Decimal('663.18')),
    ('Alimentation',   'needs',   '🛒', 'expense', Decimal('200.00')),
    ('Transport',      'needs',   '⛽', 'expense', Decimal('95.00')),
    ('Santé',          'needs',   '💊', 'expense', Decimal('55.00')),
    ('Loisirs',        'wants',   '🎬', 'expense', None),
    ('Sorties',        'wants',   '🍽️', 'expense', None),
    ('Shopping',       'wants',   '👗', 'expense', None),
    ('Abonnements',    'wants',   '📱', 'expense', None),
    ('Bien-être',      'wants',   '💆', 'expense', None),
    ('Voyages',        'wants',   '✈️', 'expense', None),
    ('Épargne',        'savings', '💰', 'expense', None),
    ('Investissement', 'savings', '📈', 'expense', None),
    ('Salaire',        'needs',   '💼', 'income',  None),
]

# ── Transactions mars 2026 ─────────────────────────────────────────────────────

MARCH = 2026

INCOME = [
    # (label, montant, jour)
    ('Virement DCS Easyware', Decimal('1699.00'), 1),
    ('Virement Perce-Neige',  Decimal('1300.00'), 1),
]

FIXED_EXPENSES = [
    # (label, montant, catégorie, jour)
    ('Loyer',    Decimal('719.00'),  'Logement', 1),
    ('Électricité', Decimal('67.00'), 'Énergie',  3),
    ('Cetelem',  Decimal('179.92'), 'Crédit',   5),
    ('Floa Bank',Decimal('113.00'), 'Crédit',   5),
    ('Cofidis',  Decimal('190.26'), 'Crédit',   5),
    ('BNP',      Decimal('180.00'), 'Crédit',   5),
]

# (label, montant_unitaire, catégorie, liste_jours)
VARIABLE_EXPENSES = [
    ('Courses alimentaires', Decimal('58.00'),  'Alimentation', [7, 14, 21]),
    ('Navigo',               Decimal('92.00'),  'Transport',    [2, 16]),
    ('Pharmacie',            Decimal('35.00'),  'Santé',        [10]),
    ('Claude AI',            Decimal('20.00'),  'Abonnements',  [8]),
    ('Restaurant',           Decimal('50.00'),  'Sorties',      [9, 23]),
    ('Café / Snack',         Decimal('16.00'),  'Sorties',      [5, 12, 19]),
    ('Vêtements',            Decimal('85.00'),  'Shopping',     [15]),
    ('Loisirs / Sorties',    Decimal('125.00'), 'Loisirs',      [20]),
    ('Coiffeur',             Decimal('37.00'),  'Bien-être',    [11]),
    ('Épargne Congo',        Decimal('250.00'), 'Voyages',      [2]),
]

# ── Objectifs d'épargne ───────────────────────────────────────────────────────

GOALS = [
    # (nom, icône, target, current, deadline, couleur, type)
    ('Voyage Congo',   '✈️', Decimal('2000.00'),  Decimal('0'),  date(2027, 3, 18), '#f59e0b', 'savings'),
    ('Fond d\'urgence','🛡️', Decimal('5000.00'),  Decimal('556.00'), date(2026, 12, 31), '#ef4444', 'savings'),
    ('Congo Famille',  '🌍', Decimal('2500.00'),  Decimal('0'),  date(2027, 3, 18), '#22c55e', 'savings'),
    ('Business perso', '🚀', Decimal('10000.00'), Decimal('0'),  date(2028, 3, 17), '#a78bfa', 'savings'),
]

# ── Comptes épargne ───────────────────────────────────────────────────────────

SAVINGS_ACCOUNTS = [
    # (nom, icône, solde, target, taux, couleur)
    ('Revolut Savings', '💳', Decimal('756.00'),  Decimal('10000.00'), Decimal('0.00'),  '#6366f1'),
    ('Livret A',        '🏦', Decimal('0.00'),   Decimal('22950.00'), Decimal('1.50'),  '#34d399'),
]

# ── Scores wants ──────────────────────────────────────────────────────────────
# calculés APRÈS création des catégories (on aura besoin des IDs)
WANTS_SCORES = {
    'Voyages':     5,
    'Sorties':     4,
    'Loisirs':     4,
    'Abonnements': 3,
    'Bien-être':   3,
    'Shopping':    2,
}


class Command(BaseCommand):
    help = 'Seed les données de Josue (mars 2026)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Supprime les données existantes avant de seeder')

    def handle(self, *args, **options):
        from apps.categories.models import Category
        from apps.transactions.models import Transaction
        from apps.goals.models import Goal
        from apps.savings.models import SavingsAccount, SavingsRule

        # ── 1. Utilisateur ────────────────────────────────────────────────────
        user, created = User.objects.get_or_create(
            username='josue',
            defaults={
                'first_name': 'Josue',
                'last_name': '',
                'email': 'josue@budgetmaster.app',
                'locale': 'fr-FR',
                'currency': 'EUR',
            }
        )
        if created:
            user.set_password('Josue@2026!')
            user.save()
            self.stdout.write(self.style.SUCCESS('✓ Utilisateur josue créé'))
        else:
            self.stdout.write('→ Utilisateur josue existant')

        if options['reset']:
            Transaction.objects.filter(user=user).delete()
            Category.objects.filter(user=user).delete()
            Goal.objects.filter(user=user).delete()
            SavingsAccount.objects.filter(user=user).delete()
            SavingsRule.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING('⚠ Données existantes supprimées'))

        # ── 2. Catégories ─────────────────────────────────────────────────────
        cat_map = {}
        for nom, bucket, icon, ctype, budget in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                user=user, name=nom,
                defaults={
                    'rule_bucket':   bucket,
                    'icon':          icon,
                    'type':          ctype,
                    'budget_limit':  budget,
                }
            )
            cat_map[nom] = cat
        self.stdout.write(f'✓ {len(cat_map)} catégories')

        # ── 3. Revenus ────────────────────────────────────────────────────────
        for label, amount, day in INCOME:
            Transaction.objects.get_or_create(
                user=user, label=label,
                date=date(MARCH, 3, day),
                defaults={
                    'amount':   amount,
                    'type':     'income',
                    'category': cat_map['Salaire'],
                }
            )
        self.stdout.write(f'✓ {len(INCOME)} revenus')

        # ── 4. Dépenses fixes ─────────────────────────────────────────────────
        for label, amount, cat_name, day in FIXED_EXPENSES:
            Transaction.objects.get_or_create(
                user=user, label=label,
                date=date(MARCH, 3, day),
                defaults={
                    'amount':      amount,
                    'type':        'expense',
                    'category':    cat_map[cat_name],
                    'is_recurring': True,
                    'recurrence':  'monthly',
                }
            )
        self.stdout.write(f'✓ {len(FIXED_EXPENSES)} dépenses fixes')

        # ── 5. Dépenses variables ─────────────────────────────────────────────
        count = 0
        for label, amount, cat_name, days in VARIABLE_EXPENSES:
            for day in days:
                Transaction.objects.get_or_create(
                    user=user, label=label,
                    date=date(MARCH, 3, day),
                    defaults={
                        'amount':   amount,
                        'type':     'expense',
                        'category': cat_map[cat_name],
                    }
                )
                count += 1
        self.stdout.write(f'✓ {count} dépenses variables')

        # ── 6. Comptes épargne ────────────────────────────────────────────────
        for nom, icon, balance, target, rate, color in SAVINGS_ACCOUNTS:
            SavingsAccount.objects.get_or_create(
                user=user, name=nom,
                defaults={
                    'icon':          icon,
                    'balance':       balance,
                    'target':        target,
                    'interest_rate': rate,
                    'color':         color,
                }
            )
        self.stdout.write(f'✓ {len(SAVINGS_ACCOUNTS)} comptes épargne')

        # ── 7. Objectifs ──────────────────────────────────────────────────────
        for nom, icon, target, current, deadline, color, gtype in GOALS:
            Goal.objects.get_or_create(
                user=user, name=nom,
                defaults={
                    'icon':           icon,
                    'target_amount':  target,
                    'current_amount': current,
                    'deadline':       deadline,
                    'color':          color,
                    'type':           gtype,
                }
            )
        self.stdout.write(f'✓ {len(GOALS)} objectifs')

        # ── 8. Règle d'épargne + scores wants ────────────────────────────────
        wants_scores_by_id = {
            str(cat_map[nom].id): score
            for nom, score in WANTS_SCORES.items()
            if nom in cat_map
        }
        rule, _ = SavingsRule.objects.get_or_create(
            user=user,
            defaults={
                'mode':            'adaptive',
                'active':          True,
                'savings_target':  Decimal('20'),
                'needs_target':    Decimal('50'),
                'wants_target':    Decimal('30'),
                'savings_tolerance': Decimal('5'),
                'needs_tolerance':   Decimal('5'),
                'wants_tolerance':   Decimal('5'),
                'savings_floor':     Decimal('15'),
                'needs_floor':       Decimal('40'),
                'wants_floor':       Decimal('10'),
                'wants_scores':      wants_scores_by_id,
            }
        )
        if not rule.wants_scores:
            rule.wants_scores = wants_scores_by_id
            rule.save(update_fields=['wants_scores'])
        self.stdout.write(f'✓ Règle 50/30/20 + scores wants')

        # ── Résumé ────────────────────────────────────────────────────────────
        income_total = sum(t for _, t, _ in INCOME)
        fixed_total  = sum(t for _, t, _, _ in FIXED_EXPENSES)
        var_total    = sum(t * len(days) for _, t, _, days in VARIABLE_EXPENSES)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════'))
        self.stdout.write(self.style.SUCCESS(f'  Josue — Résumé mars 2026'))
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════'))
        self.stdout.write(f'  Revenus       : {income_total:>10.2f} €')
        self.stdout.write(f'  Dépenses fixes: {fixed_total:>10.2f} €')
        self.stdout.write(f'  Dépenses var. : {var_total:>10.2f} €')
        self.stdout.write(f'  Solde estimé  : {income_total - fixed_total - var_total:>10.2f} €')
        self.stdout.write(self.style.SUCCESS('  → Connexion : josue / Josue@2026!'))
