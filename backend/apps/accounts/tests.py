"""
Tests — BankAccount model + history + summary + API
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import BankAccount
from apps.transactions.models import Transaction

User = get_user_model()


def make_user(username, password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def auth_client(username, password='testpass123'):
    user = make_user(username, password)
    client = APIClient()
    res = client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client, user


def make_account(user, **kwargs):
    defaults = dict(name='Compte Test', bank_name='BNP', account_type='checking',
                    initial_balance=Decimal('1000.00'), color='#00D4AA', icon='🏦')
    defaults.update(kwargs)
    return BankAccount.objects.create(user=user, **defaults)


# ─── Model ──────────────────────────────────────────────────────────────────

class BankAccountModelTest(TestCase):

    def setUp(self):
        self.user = make_user('acc_model')

    def test_create_account(self):
        acc = make_account(self.user)
        self.assertEqual(str(acc), f"Compte Test ({self.user})")

    def test_isolation_between_users(self):
        u2 = make_user('acc_model2')
        make_account(self.user, name='Mine')
        make_account(u2, name='Other')
        my_names = list(BankAccount.objects.filter(user=self.user).values_list('name', flat=True))
        self.assertIn('Mine', my_names)
        self.assertNotIn('Other', my_names)

    def test_default_values(self):
        acc = make_account(self.user)
        self.assertEqual(acc.account_type, 'checking')
        self.assertFalse(acc.is_default)


# ─── API CRUD ────────────────────────────────────────────────────────────────

class BankAccountAPITest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('acc_api')

    def test_create_account(self):
        res = self.client.post('/api/accounts/', {
            'name': 'Compte Courant', 'bank_name': 'Crédit Agricole',
            'account_type': 'checking', 'initial_balance': '500.00',
            'color': '#3b82f6', 'icon': '💳',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['name'], 'Compte Courant')

    def test_list_returns_only_own_accounts(self):
        _, other = auth_client('acc_other')
        make_account(other, name='Compte autre')
        make_account(self.user, name='Mon compte')
        res = self.client.get('/api/accounts/')
        names = [a['name'] for a in (res.data.get('results', res.data))]
        self.assertIn('Mon compte', names)
        self.assertNotIn('Compte autre', names)

    def test_update_account(self):
        acc = make_account(self.user, name='Ancien nom')
        res = self.client.patch(f'/api/accounts/{acc.id}/', {'name': 'Nouveau nom'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'Nouveau nom')

    def test_delete_account(self):
        acc = make_account(self.user)
        res = self.client.delete(f'/api/accounts/{acc.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(BankAccount.objects.filter(pk=acc.id).exists())

    def test_cannot_access_other_users_account(self):
        _, other = auth_client('acc_other2')
        acc = make_account(other, name='Pas à moi')
        res = self.client.get(f'/api/accounts/{acc.id}/')
        self.assertIn(res.status_code, [403, 404])

    def test_unauthenticated_returns_401(self):
        res = APIClient().get('/api/accounts/')
        self.assertEqual(res.status_code, 401)


# ─── Summary ─────────────────────────────────────────────────────────────────

class BankAccountSummaryTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('acc_summary')

    def test_summary_empty(self):
        res = self.client.get('/api/accounts/summary/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['account_count'], 0)
        self.assertEqual(res.data['total_balance'], 0.0)

    def test_summary_with_initial_balance(self):
        make_account(self.user, initial_balance=Decimal('2000.00'))
        make_account(self.user, initial_balance=Decimal('500.00'))
        res = self.client.get('/api/accounts/summary/')
        self.assertEqual(res.data['account_count'], 2)
        self.assertAlmostEqual(res.data['total_balance'], 2500.0, places=1)

    def test_summary_with_transactions(self):
        acc = make_account(self.user, initial_balance=Decimal('1000.00'))
        Transaction.objects.create(
            user=self.user, label='Salaire', amount=Decimal('2000'), type='income',
            date=date.today(), bank_account=acc,
        )
        Transaction.objects.create(
            user=self.user, label='Loyer', amount=Decimal('800'), type='expense',
            date=date.today(), bank_account=acc,
        )
        res = self.client.get('/api/accounts/summary/')
        # 1000 (initial) + 2000 (income) - 800 (expense) = 2200
        self.assertAlmostEqual(res.data['total_balance'], 2200.0, places=1)


# ─── History ─────────────────────────────────────────────────────────────────

class BankAccountHistoryTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('acc_hist')
        self.acc = make_account(self.user, initial_balance=Decimal('1000.00'))

    def test_history_empty(self):
        res = self.client.get(f'/api/accounts/{self.acc.id}/history/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_history_shows_monthly_balance(self):
        Transaction.objects.create(
            user=self.user, label='Salaire', amount=Decimal('3000'), type='income',
            date=date(2026, 1, 15), bank_account=self.acc,
        )
        Transaction.objects.create(
            user=self.user, label='Loyer', amount=Decimal('800'), type='expense',
            date=date(2026, 1, 20), bank_account=self.acc,
        )
        res = self.client.get(f'/api/accounts/{self.acc.id}/history/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        entry = res.data[0]
        self.assertEqual(entry['month'], '2026-01')
        self.assertAlmostEqual(entry['income'], 3000.0, places=1)
        self.assertAlmostEqual(entry['expenses'], 800.0, places=1)
        # balance = 1000 (initial) + 3000 - 800 = 3200
        self.assertAlmostEqual(entry['balance'], 3200.0, places=1)

    def test_history_accumulates_across_months(self):
        Transaction.objects.create(
            user=self.user, label='Jan income', amount=Decimal('1000'), type='income',
            date=date(2026, 1, 5), bank_account=self.acc,
        )
        Transaction.objects.create(
            user=self.user, label='Feb expense', amount=Decimal('200'), type='expense',
            date=date(2026, 2, 5), bank_account=self.acc,
        )
        res = self.client.get(f'/api/accounts/{self.acc.id}/history/')
        self.assertEqual(len(res.data), 2)
        # Feb balance = 1000 (initial) + 1000 (jan) - 200 (feb) = 1800
        self.assertAlmostEqual(res.data[1]['balance'], 1800.0, places=1)
