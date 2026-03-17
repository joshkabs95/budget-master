"""
Seed data basé sur le relevé BNP Paribas de Josué KABANGU KAZADI
Période : 28 janvier – 28 février 2026
Compte   : IBAN FR76 3000 4007 6100 0012 4320 329
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed data réel depuis le relevé BNP de Josué Kabangu'

    def handle(self, *args, **kwargs):
        from apps.categories.models import Category
        from apps.transactions.models import Transaction
        from apps.savings.models import SavingsAccount, SavingsRule
        from apps.goals.models import Goal

        self.stdout.write('🌱 Seeding data depuis le relevé BNP Paribas...')

        # ── Utilisateur ──────────────────────────────────────────────────────
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'josue.kabangu@budgetmaster.fr',
                'first_name': 'Josué',
                'last_name': 'Kabangu Kazadi',
                'locale': 'fr-FR',
                'currency': 'EUR',
            }
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write('✅ Utilisateur "demo" créé (password: demo1234)')
        else:
            self.stdout.write('ℹ️  Utilisateur "demo" déjà existant')

        # Purge données existantes
        Transaction.objects.filter(user=user).delete()
        Category.objects.filter(user=user).delete()
        SavingsAccount.objects.filter(user=user).delete()
        SavingsRule.objects.filter(user=user).delete()
        Goal.objects.filter(user=user).delete()

        # ── Catégories ────────────────────────────────────────────────────────
        cats = {
            # Revenus
            'salaire':       Category.objects.create(
                user=user, name='Salaire', icon='💼', color='#22c55e',
                type='income', rule_bucket='needs', budget_limit=0),
            'remboursements': Category.objects.create(
                user=user, name='Remboursements reçus', icon='↩️', color='#4ade80',
                type='income', rule_bucket='needs', budget_limit=0),

            # Besoins (needs)
            'logement':      Category.objects.create(
                user=user, name='Logement & Famille', icon='🏠', color='#3b82f6',
                type='expense', rule_bucket='needs', budget_limit=1700),
            'pret':          Category.objects.create(
                user=user, name='Prêt immobilier', icon='🏦', color='#1d4ed8',
                type='expense', rule_bucket='needs', budget_limit=200),
            'alimentation':  Category.objects.create(
                user=user, name='Alimentation', icon='🛒', color='#16a34a',
                type='expense', rule_bucket='needs', budget_limit=250),
            'transport':     Category.objects.create(
                user=user, name='Transport', icon='🚗', color='#f97316',
                type='expense', rule_bucket='needs', budget_limit=80),
            'abonnements':   Category.objects.create(
                user=user, name='Abonnements', icon='📱', color='#6b7280',
                type='expense', rule_bucket='needs', budget_limit=60),
            'frais_banque':  Category.objects.create(
                user=user, name='Frais bancaires', icon='🏛️', color='#94a3b8',
                type='expense', rule_bucket='needs', budget_limit=15),
            'retraits':      Category.objects.create(
                user=user, name='Retraits DAB', icon='💵', color='#78716c',
                type='expense', rule_bucket='needs', budget_limit=100),

            # Envies (wants)
            'shopping':      Category.objects.create(
                user=user, name='Shopping', icon='🛍️', color='#a855f7',
                type='expense', rule_bucket='wants', budget_limit=150),
            'cosmetiques':   Category.objects.create(
                user=user, name='Beauté & Cosmétiques', icon='💄', color='#ec4899',
                type='expense', rule_bucket='wants', budget_limit=60),
            'restaurants':   Category.objects.create(
                user=user, name='Restaurants & Bars', icon='🍽️', color='#f59e0b',
                type='expense', rule_bucket='wants', budget_limit=80),
            'services_ia':   Category.objects.create(
                user=user, name='Services IA', icon='🤖', color='#8b5cf6',
                type='expense', rule_bucket='wants', budget_limit=40),
            'services_web':  Category.objects.create(
                user=user, name='Services web & Tech', icon='🌐', color='#0ea5e9',
                type='expense', rule_bucket='wants', budget_limit=20),
            'envois':        Category.objects.create(
                user=user, name='Envois & Transferts', icon='💸', color='#ef4444',
                type='expense', rule_bucket='wants', budget_limit=100),
        }
        self.stdout.write('✅ Catégories créées')

        # ── Comptes épargne ───────────────────────────────────────────────────
        revolut = SavingsAccount.objects.create(
            user=user, name='Revolut Savings', icon='💳', color='#3b82f6',
            balance=0, target=10000, interest_rate=0,
        )
        livret_a = SavingsAccount.objects.create(
            user=user, name='Livret A', icon='🏦', color='#22c55e',
            balance=0, target=22950, interest_rate=1.5,
        )
        self.stdout.write('✅ Comptes épargne créés')

        # ── Règle adaptative ──────────────────────────────────────────────────
        SavingsRule.objects.create(
            user=user,
            savings_target=20, needs_target=50, wants_target=30,
            savings_tolerance=5, needs_tolerance=5, wants_tolerance=5,
            savings_floor=15, needs_floor=40, wants_floor=10,
            compensation_order=['wants', 'needs'],
            window_months=3, catchup_max_months=3,
            mode='adaptive', active=True,
        )
        self.stdout.write('✅ Règle adaptative créée')

        # ── Objectifs ─────────────────────────────────────────────────────────
        today = date.today()
        from datetime import timedelta
        goals_data = [
            # Court terme — rembourser Celjya
            {'name': 'Remboursement Celjya', 'type': 'expense',
             'target_amount': 800, 'current_amount': 0,
             'deadline': today + timedelta(days=45),
             'icon': '↩️', 'color': '#f97316', 'savings_account': None},
            # Moyen terme — fonds d'urgence
            {'name': 'Fonds d\'urgence 3 mois', 'type': 'savings',
             'target_amount': 7000, 'current_amount': 556,
             'deadline': today + timedelta(days=270),
             'icon': '🛡️', 'color': '#3b82f6', 'savings_account': revolut},
            # Long terme — apport immobilier
            {'name': 'Apport immobilier', 'type': 'savings',
             'target_amount': 30000, 'current_amount': 0,
             'deadline': today + timedelta(days=730),
             'icon': '🏠', 'color': '#a855f7', 'savings_account': livret_a},
            # Long terme — voyage Congo
            {'name': 'Voyage Congo', 'type': 'expense',
             'target_amount': 2500, 'current_amount': 0,
             'deadline': today + timedelta(days=365),
             'icon': '✈️', 'color': '#c9a84c', 'savings_account': None},
        ]
        for g in goals_data:
            sa = g.pop('savings_account')
            Goal.objects.create(user=user, savings_account=sa, **g)
        self.stdout.write('✅ Objectifs créés')

        # ── Transactions réelles du relevé ────────────────────────────────────
        # Revenus net des salaires du mois : 1798.88 + 560.57 = 2359.45 €
        # Épargne Revolut : 550 + 6 = 556 € = 23.6% ✅
        # Besoins : Loyer(1470) + Prêt(189.69) + Ali + Transport + Abo = 84% ❌
        # Envies  : Shopping + Restau + IA + Envois = ~16% (sous-utilisé)
        # ─→ Scénario réel : besoins en dépassement critique (loyer seul = 62%)

        txns = []

        def T(d, label, cat, amount, typ='expense', src='import', sa=None):
            return {
                'date': d, 'label': label, 'category': cat,
                'amount': Decimal(str(amount)), 'type': typ,
                'source': src, 'savings_account': sa,
            }

        # ── JANVIER 2026 (estimé sur pattern connu) ──────────────────────────
        txns += [
            # Revenus janvier
            T(date(2026, 1, 5),  'Salaire DCS EASYWARE – 12/2025',   cats['salaire'],    1798.88, 'income'),
            T(date(2026, 1, 25), 'Salaire Fondation Perceneige – 12/2025', cats['salaire'], 560.57, 'income'),

            # Besoins janvier
            T(date(2026, 1, 3),  'Virement Karnelle Kabangu – Loyer & charges', cats['logement'], 1470.00),
            T(date(2026, 1, 4),  'Échéance prêt immobilier',           cats['pret'],       189.69),
            T(date(2026, 1, 8),  'Carrefour Conflans – Courses',        cats['alimentation'], 45.20),
            T(date(2026, 1, 12), 'Monoprix – Courses',                  cats['alimentation'], 22.50),
            T(date(2026, 1, 15), 'Franprix Paris – Express',            cats['alimentation'], 8.90),
            T(date(2026, 1, 18), 'Bolt.eu – VTC',                       cats['transport'],    12.40),
            T(date(2026, 1, 5),  'Adobe – Abonnement Creative Cloud',   cats['abonnements'],  35.99),
            T(date(2026, 1, 5),  'Adobe – Acrobat Pro',                 cats['abonnements'],   8.05),
            T(date(2026, 1, 10), 'Cotisation Esprit Libre – BNP',       cats['frais_banque'],  7.03),
            T(date(2026, 1, 15), 'Retrait DAB – LCL Conflans',          cats['retraits'],      50.00),
            T(date(2026, 1, 20), 'Retrait DAB – La Banque Postale',     cats['retraits'],      50.00),

            # Envies janvier
            T(date(2026, 1, 16), 'Klarna – Vêtements en ligne',         cats['shopping'],     89.00),
            T(date(2026, 1, 20), 'Anthropic API',                        cats['services_ia'],   6.14),
            T(date(2026, 1, 22), 'Wero – Envoi Jerome K.',               cats['envois'],        15.00),
            T(date(2026, 1, 25), 'Western Union – Transfert famille',    cats['envois'],        60.00),

            # Épargne janvier
            T(date(2026, 1, 28), 'Virement Revolut – Épargne',
              None, 200.00, 'saving', 'manual', revolut),
        ]

        # ── FÉVRIER 2026 — données réelles du relevé BNP ─────────────────────

        # ─ REVENUS ─
        txns += [
            T(date(2026, 2, 2),  'Salaire DCS EASYWARE – 01/2026',
              cats['salaire'],    1798.88, 'income', 'import'),
            T(date(2026, 2, 2),  'Virement reçu – Josué Kabangu (depuis Revolut)',
              cats['remboursements'], 100.00, 'income', 'import'),
            T(date(2026, 2, 6),  'Remboursement – Patrick Amanako Kashama',
              cats['remboursements'], 80.00, 'income', 'import'),
            T(date(2026, 2, 12), 'Remboursement – Mme Abrantes da Silva Celjya',
              cats['remboursements'], 800.00, 'income', 'import'),
            T(date(2026, 2, 23), 'Remboursement – M. Christo Balumuenetshitala',
              cats['remboursements'], 10.00, 'income', 'import'),
            T(date(2026, 2, 26), 'Salaire Fondation Perceneige – 02/2026',
              cats['salaire'],    560.57, 'income', 'import'),
        ]

        # ─ BESOINS ─
        txns += [
            # Logement / famille
            T(date(2026, 1, 27), 'Klarna* H&M Online – Mode',
              cats['shopping'],   63.75, 'expense', 'import'),
            T(date(2026, 2, 3),  'Virement Karnelle Kabangu Kazadi – Loyer & charges',
              cats['logement'],  1470.00, 'expense', 'import'),
            T(date(2026, 2, 4),  'Échéance prêt immobilier 0147061186482',
              cats['pret'],       189.69, 'expense', 'import'),

            # Frais bancaires
            T(date(2026, 2, 3),  'Commissions retraits DAB déplacés',
              cats['frais_banque'], 2.40, 'expense', 'import'),
            T(date(2026, 2, 3),  'Cotisation Esprit Libre – BNP Paribas',
              cats['frais_banque'], 7.03, 'expense', 'import'),

            # Abonnements
            T(date(2026, 2, 6),  'Adobe – Acrobat Pro',
              cats['abonnements'],  8.05, 'expense', 'import'),
            T(date(2026, 2, 6),  'Adobe – Creative Cloud',
              cats['abonnements'], 35.99, 'expense', 'import'),

            # Retraits DAB
            T(date(2026, 2, 6),  'Retrait DAB – La Banque Postale Cergy (1)',
              cats['retraits'],    50.00, 'expense', 'import'),
            T(date(2026, 2, 6),  'Retrait DAB – La Banque Postale Cergy (2)',
              cats['retraits'],    50.00, 'expense', 'import'),
            T(date(2026, 2, 9),  'Retrait DAB – LCL Conflans-Ste-Honorine',
              cats['retraits'],    50.00, 'expense', 'import'),
            T(date(2026, 2, 23), 'Retrait DAB – LCL Brunoy',
              cats['retraits'],    20.00, 'expense', 'import'),
            T(date(2026, 2, 26), 'Retrait DAB – LCL Brunoy',
              cats['retraits'],    20.00, 'expense', 'import'),

            # Transport
            T(date(2026, 2, 23), 'Bolt.eu – VTC',
              cats['transport'],   10.80, 'expense', 'import'),

            # Alimentation
            T(date(2026, 2, 11), 'Kokul – Sartrouville',
              cats['alimentation'], 3.60, 'expense', 'import'),
            T(date(2026, 2, 11), 'BNB Distribution – Cergy',
              cats['alimentation'], 5.89, 'expense', 'import'),
            T(date(2026, 2, 12), 'Carrefour City – Paris',
              cats['alimentation'], 3.20, 'expense', 'import'),
            T(date(2026, 2, 13), 'JJN Alimentation',
              cats['alimentation'], 1.70, 'expense', 'import'),
            T(date(2026, 2, 13), 'Monoprix – Paris 14',
              cats['alimentation'], 4.84, 'expense', 'import'),
            T(date(2026, 2, 13), 'Newg.B Trading – Paris 18',
              cats['alimentation'], 7.00, 'expense', 'import'),
            T(date(2026, 2, 16), 'BMosny – Osny',
              cats['alimentation'], 31.41, 'expense', 'import'),
            T(date(2026, 2, 17), 'SC-Knhalim – Mandres-les-Roses',
              cats['alimentation'], 1.70, 'expense', 'import'),
            T(date(2026, 2, 17), 'Monoprix – Brunoy',
              cats['alimentation'], 3.39, 'expense', 'import'),
            T(date(2026, 2, 17), 'Sasoz – Mandres-les-Roses',
              cats['alimentation'], 9.50, 'expense', 'import'),
            T(date(2026, 2, 18), 'Franprix – Paris',
              cats['alimentation'], 4.29, 'expense', 'import'),
            T(date(2026, 2, 24), 'Carrefour – Boulogne-Billancourt',
              cats['alimentation'], 2.15, 'expense', 'import'),
            T(date(2026, 2, 26), 'Le Marché Franprix – Paris',
              cats['alimentation'], 5.65, 'expense', 'import'),
            T(date(2026, 2, 27), 'JJN Alimentation (1)',
              cats['alimentation'], 3.40, 'expense', 'import'),
            T(date(2026, 2, 27), 'JJN Alimentation – Conflans-Ste-Honorine',
              cats['alimentation'], 3.40, 'expense', 'import'),
            T(date(2026, 2, 27), 'P. des Marinières – Conflans-Ste-Honorine',
              cats['alimentation'], 8.70, 'expense', 'import'),
        ]

        # ─ ENVIES ─
        txns += [
            # Shopping (Klarna)
            T(date(2026, 2, 12), 'Klarna* Sephora – Beauté',
              cats['cosmetiques'],  47.88, 'expense', 'import'),
            T(date(2026, 2, 13), 'Paris Forum II – Shopping',
              cats['shopping'],     17.00, 'expense', 'import'),
            T(date(2026, 2, 16), 'Klarna* Temu.com – Shopping en ligne',
              cats['shopping'],     30.28, 'expense', 'import'),
            T(date(2026, 2, 16), 'Klarna* Klarna – Shopping',
              cats['shopping'],     19.99, 'expense', 'import'),
            T(date(2026, 2, 20), 'Klarna* Klarna M – Shopping',
              cats['shopping'],      1.99, 'expense', 'import'),
            T(date(2026, 2, 27), 'HL Cosmetics – Beauté',
              cats['cosmetiques'],  10.00, 'expense', 'import'),

            # Restaurants & bars
            T(date(2026, 2, 17), 'Brasserie l\'Europe – Paris',
              cats['restaurants'],  10.00, 'expense', 'import'),
            T(date(2026, 2, 20), 'SC-California – Paris',
              cats['restaurants'],  20.00, 'expense', 'import'),

            # Services IA (Anthropic / Claude)
            T(date(2026, 2, 9),  'Anthropic API – Février (1)',
              cats['services_ia'],   6.14, 'expense', 'import'),
            T(date(2026, 2, 25), 'Anthropic API – Février (2)',
              cats['services_ia'],   7.19, 'expense', 'import'),
            T(date(2026, 2, 27), 'Claude.ai – Abonnement mensuel',
              cats['services_ia'],  21.60, 'expense', 'import'),

            # Services web
            T(date(2026, 2, 20), 'Hostinger.com – Hébergement web',
              cats['services_web'], 11.99, 'expense', 'import'),

            # Envois & transferts familiaux
            T(date(2026, 2, 27), 'Wero – Envoi à Jérôme K.',
              cats['envois'],       11.00, 'expense', 'import'),
            T(date(2026, 2, 27), 'Wero – Envoi à Jonathan Gaibilimwamba',
              cats['envois'],       20.00, 'expense', 'import'),
            T(date(2026, 2, 27), 'Wero – Envoi à Ingrid N. (1)',
              cats['envois'],       40.00, 'expense', 'import'),
            T(date(2026, 2, 27), 'Wero – Envoi à Ingrid N. (2)',
              cats['envois'],       50.00, 'expense', 'import'),
            T(date(2026, 2, 27), 'Western Union – Transfert international (1)',
              cats['envois'],       51.99, 'expense', 'import'),
            T(date(2026, 2, 27), 'Western Union Vienna – Transfert (1)',
              cats['envois'],       45.21, 'expense', 'import'),
            T(date(2026, 2, 27), 'Western Union Vienna – Transfert (2)',
              cats['envois'],       88.44, 'expense', 'import'),

            # Virement billets/cash vers Revolut (29 jan)
            T(date(2026, 1, 29), 'Virement Revolut – Billets / cash voyage',
              cats['retraits'],   1800.00, 'expense', 'import'),
        ]

        # ─ ÉPARGNE Revolut (virements Feb) ─
        txns += [
            T(date(2026, 2, 16), 'Virement Revolut – Épargne mensuelle',
              None, 500.00, 'saving', 'import', revolut),
            T(date(2026, 2, 16), 'Virement Revolut – Épargne complementaire',
              None,  50.00, 'saving', 'import', revolut),
            T(date(2026, 2, 25), 'Virement Revolut – Micro-épargne (1)',
              None,   2.00, 'saving', 'import', revolut),
            T(date(2026, 2, 25), 'Virement Revolut – Micro-épargne (2)',
              None,   4.00, 'saving', 'import', revolut),
        ]

        # ── Insertion ─────────────────────────────────────────────────────────
        for t in txns:
            Transaction.objects.create(user=user, **t)

        revolut.recalculate_balance()
        livret_a.recalculate_balance()

        self.stdout.write(f'✅ {len(txns)} transactions importées')
        self.stdout.write('')
        self.stdout.write('🎉 Seed terminé ! Login: demo / demo1234')
        self.stdout.write('')
        self.stdout.write('📊 Analyse du relevé BNP (Feb 2026) :')
        self.stdout.write('   Revenus salaires : 2 359.45 €')
        self.stdout.write('   Épargne Revolut  :   556.00 € = 23.6% ✅')
        self.stdout.write('   Besoins (loyer+prêt seul) : 1 659.69 € = 70.3% ❌ ALERTE')
        self.stdout.write('   → Scénario : besoins > 50% cible → plan de compensation')
        self.stdout.write('   Solde ouverture : 1 886.93 €  |  Clôture : 292.15 €')
