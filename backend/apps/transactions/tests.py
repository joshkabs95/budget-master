"""
Tests — Transaction model + categorization + import_hash + API endpoints
"""
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.transactions.models import Transaction
from apps.transactions.services.categorization import categorize_label, compute_import_hash
from apps.categories.models import Category, CategoryRule

User = get_user_model()


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_user(username='u', password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def make_transaction(user, **kwargs):
    defaults = dict(
        label='Test dépense',
        amount=Decimal('50.00'),
        type='expense',
        date=date.today(),
    )
    defaults.update(kwargs)
    return Transaction.objects.create(user=user, **defaults)


# ─── Model ──────────────────────────────────────────────────────────────────

class TransactionModelTest(TestCase):

    def setUp(self):
        self.user = make_user('model_user')

    def test_create_transaction(self):
        t = make_transaction(self.user)
        self.assertEqual(t.type, 'expense')
        self.assertEqual(t.amount, Decimal('50.00'))

    def test_str_representation(self):
        t = make_transaction(self.user, label='Loyer', amount=Decimal('800'))
        self.assertIn('Loyer', str(t))
        self.assertIn('800', str(t))

    def test_ordering_most_recent_first(self):
        yesterday = date.today() - timedelta(days=1)
        t1 = make_transaction(self.user, date=date.today(), label='Aujourd\'hui')
        t2 = make_transaction(self.user, date=yesterday, label='Hier')
        qs = Transaction.objects.filter(user=self.user)
        self.assertEqual(qs.first(), t1)

    def test_import_hash_unique_per_user(self):
        """Deux users peuvent avoir le même hash — pas de contrainte globale."""
        user2 = make_user('model_user2')
        h = compute_import_hash('2026-01-01', '50.00', 'salaire')
        make_transaction(self.user, import_hash=h)
        # Doit réussir pour un autre user
        t2 = make_transaction(user2, import_hash=h)
        self.assertEqual(t2.import_hash, h)

    def test_import_hash_unique_within_user(self):
        """Un user ne peut pas importer deux fois la même transaction."""
        from django.db import IntegrityError
        h = compute_import_hash('2026-01-01', '50.00', 'doublon')
        make_transaction(self.user, import_hash=h)
        with self.assertRaises(IntegrityError):
            make_transaction(self.user, import_hash=h)

    def test_null_import_hash_not_constrained(self):
        """Plusieurs transactions sans hash (manuelles) sont autorisées."""
        make_transaction(self.user, import_hash=None)
        make_transaction(self.user, import_hash=None)
        self.assertEqual(Transaction.objects.filter(user=self.user, import_hash__isnull=True).count(), 2)


# ─── compute_import_hash ────────────────────────────────────────────────────

class ImportHashTest(TestCase):

    def test_deterministic(self):
        h1 = compute_import_hash('2026-01-15', '123.45', 'SNCF PARIS')
        h2 = compute_import_hash('2026-01-15', '123.45', 'SNCF PARIS')
        self.assertEqual(h1, h2)

    def test_case_insensitive(self):
        h1 = compute_import_hash('2026-01-15', '123.45', 'sncf paris')
        h2 = compute_import_hash('2026-01-15', '123.45', 'SNCF PARIS')
        self.assertEqual(h1, h2)

    def test_whitespace_normalized(self):
        h1 = compute_import_hash('2026-01-15', '50.00', 'virement  salaire')
        h2 = compute_import_hash('2026-01-15', '50.00', 'virement salaire')
        self.assertEqual(h1, h2)

    def test_different_amounts_differ(self):
        h1 = compute_import_hash('2026-01-15', '50.00', 'loyer')
        h2 = compute_import_hash('2026-01-15', '51.00', 'loyer')
        self.assertNotEqual(h1, h2)

    def test_different_dates_differ(self):
        h1 = compute_import_hash('2026-01-15', '50.00', 'loyer')
        h2 = compute_import_hash('2026-01-16', '50.00', 'loyer')
        self.assertNotEqual(h1, h2)

    def test_returns_64_hex_chars(self):
        h = compute_import_hash('2026-01-01', '0.00', 'test')
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in h))


# ─── categorize_label ───────────────────────────────────────────────────────

class CategorizeLabelTest(TestCase):

    def test_known_keyword_carrefour(self):
        result = categorize_label('CARREFOUR MARKET')
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Alimentation')

    def test_known_keyword_netflix(self):
        result = categorize_label('NETFLIX')
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Loisirs')

    def test_known_keyword_sncf(self):
        result = categorize_label('SNCF BILLET TGV')
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Transport')

    def test_unknown_label_returns_none(self):
        result = categorize_label('XYZPAYMENT999UNKNOWN')
        self.assertIsNone(result)

    def test_user_rule_takes_priority(self):
        user = make_user('cat_user')
        cat = Category.objects.create(
            user=user, name='Ma Boutique', icon='🛍', color='#fff', type='expense', rule_bucket='wants'
        )
        CategoryRule.objects.create(user=user, keyword='boutique', category=cat, priority=10)
        result = categorize_label('Boutique Paris Marais', user=user)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Ma Boutique')
        self.assertEqual(result['category_id'], cat.id)

    def test_user_rule_higher_priority_wins(self):
        user = make_user('cat_user2')
        cat_low = Category.objects.create(user=user, name='Générique', icon='📦', color='#aaa', type='expense', rule_bucket='needs')
        cat_high = Category.objects.create(user=user, name='Spécifique', icon='⭐', color='#bbb', type='expense', rule_bucket='wants')
        CategoryRule.objects.create(user=user, keyword='amazon', category=cat_low, priority=0)
        CategoryRule.objects.create(user=user, keyword='amazon prime', category=cat_high, priority=5)
        result = categorize_label('AMAZON PRIME VIDEO', user=user)
        self.assertEqual(result['name'], 'Spécifique')

    def test_confidence_score_present(self):
        result = categorize_label('loyer mensuel appartement')
        self.assertIsNotNone(result)
        self.assertIn('confidence', result)
        self.assertGreater(result['confidence'], 0)


# ─── API Endpoints ──────────────────────────────────────────────────────────

class TransactionAPITest(TestCase):

    def setUp(self):
        self.user = make_user('api_user')
        self.client = APIClient()
        # Obtain JWT
        response = self.client.post('/api/auth/login/', {'username': 'api_user', 'password': 'testpass123'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])

    def test_list_empty(self):
        res = self.client.get('/api/transactions/')
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 0)

    def test_create_transaction(self):
        payload = {'label': 'Café', 'amount': '3.50', 'type': 'expense', 'date': str(date.today())}
        res = self.client.post('/api/transactions/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['label'], 'Café')

    def test_list_returns_only_own_transactions(self):
        other = make_user('other_api')
        make_transaction(other, label='Transaction autre user')
        make_transaction(self.user, label='Ma transaction')
        res = self.client.get('/api/transactions/')
        results = res.data.get('results', res.data)
        labels = [t['label'] for t in results]
        self.assertIn('Ma transaction', labels)
        self.assertNotIn('Transaction autre user', labels)

    def test_delete_own_transaction(self):
        t = make_transaction(self.user, label='À supprimer')
        res = self.client.delete(f'/api/transactions/{t.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Transaction.objects.filter(pk=t.id).exists())

    def test_cannot_delete_other_users_transaction(self):
        other = make_user('other_api2')
        t = make_transaction(other, label='Pas à moi')
        res = self.client.delete(f'/api/transactions/{t.id}/')
        self.assertIn(res.status_code, [403, 404])
        self.assertTrue(Transaction.objects.filter(pk=t.id).exists())

    def test_stats_endpoint(self):
        make_transaction(self.user, amount=Decimal('1000'), type='income')
        make_transaction(self.user, amount=Decimal('400'), type='expense')
        month = str(date.today())[:7]
        res = self.client.get(f'/api/transactions/stats/?month={month}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('income', res.data)
        self.assertIn('expenses', res.data)

    def test_unauthenticated_returns_401(self):
        unauth = APIClient()
        res = unauth.get('/api/transactions/')
        self.assertEqual(res.status_code, 401)
