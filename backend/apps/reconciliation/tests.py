"""
Tests — Reconciliation: session creation, CSV parsing, matching, manual match, close
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.reconciliation.models import ReconciliationSession, ReconciliationEntry
from apps.transactions.models import Transaction

User = get_user_model()


def auth_client(username, password='testpass123'):
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    res = client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client, User.objects.get(username=username)


SIMPLE_CSV = "Date;Libellé;Montant\n15/01/2026;CARREFOUR;-45.50\n20/01/2026;SALAIRE;+2500.00\n"
EMPTY_CSV = "Date;Libellé;Montant\n"
INVALID_CSV = "champ1;champ2\nvaleur1;valeur2\n"


# ─── Session ─────────────────────────────────────────────────────────────────

class ReconciliationSessionTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('rec_session')

    def test_start_creates_session(self):
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertIn(res.status_code, [200, 201], res.data)
        self.assertTrue(ReconciliationSession.objects.filter(user=self.user, month='2026-01').exists())

    def test_start_missing_month_returns_400(self):
        res = self.client.post('/api/reconciliation/start/', {
            'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_start_empty_csv_returns_400(self):
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': EMPTY_CSV,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_start_invalid_csv_returns_400(self):
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': INVALID_CSV,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_start_idempotent_reopens_session(self):
        self.client.post('/api/reconciliation/start/', {
            'month': '2026-01', 'csv_content': SIMPLE_CSV,
        }, format='json')
        self.client.post('/api/reconciliation/start/', {
            'month': '2026-01', 'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertEqual(ReconciliationSession.objects.filter(user=self.user, month='2026-01').count(), 1)

    def test_cannot_reopen_closed_session(self):
        ReconciliationSession.objects.create(user=self.user, month='2026-02', status='closed')
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-02', 'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_list_sessions_isolation(self):
        _, other = auth_client('rec_other')
        ReconciliationSession.objects.create(user=other, month='2026-03', status='open')
        ReconciliationSession.objects.create(user=self.user, month='2026-04', status='open')
        res = self.client.get('/api/reconciliation/')
        results = res.data.get('results', res.data)
        months = [s['month'] for s in results]
        self.assertIn('2026-04', months)
        self.assertNotIn('2026-03', months)

    def test_unauthenticated_returns_401(self):
        res = APIClient().post('/api/reconciliation/start/', {
            'month': '2026-01', 'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertEqual(res.status_code, 401)


# ─── Matching ────────────────────────────────────────────────────────────────

class ReconciliationMatchTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('rec_match')

    def test_matched_transaction_creates_auto_entry(self):
        Transaction.objects.create(
            user=self.user, label='CARREFOUR', amount=Decimal('45.50'),
            type='expense', date=date(2026, 1, 15),
        )
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': "Date;Libellé;Montant\n15/01/2026;CARREFOUR;-45.50\n",
        }, format='json')
        self.assertIn(res.status_code, [200, 201])
        session = ReconciliationSession.objects.get(user=self.user, month='2026-01')
        auto_entries = session.entries.filter(status='auto')
        self.assertGreater(auto_entries.count(), 0)

    def test_unmatched_bank_entry_is_created(self):
        # No app transactions for this month
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertIn(res.status_code, [200, 201])
        session = ReconciliationSession.objects.get(user=self.user, month='2026-01')
        unmatched = session.entries.filter(status='unmatched_bank')
        self.assertGreater(unmatched.count(), 0)

    def test_response_contains_entries(self):
        res = self.client.post('/api/reconciliation/start/', {
            'month': '2026-01',
            'csv_content': SIMPLE_CSV,
        }, format='json')
        self.assertIn('entries', res.data)
        self.assertIsInstance(res.data['entries'], list)


# ─── Close session ───────────────────────────────────────────────────────────

class ReconciliationCloseTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('rec_close')

    def test_close_session(self):
        # Create a session and match the one bank entry with an app transaction
        csv = "Date;Libellé;Montant\n15/01/2026;SALAIRE;+2500.00\n"
        txn = Transaction.objects.create(
            user=self.user, label='SALAIRE', amount=Decimal('2500.00'),
            type='income', date=date(2026, 1, 15),
        )
        self.client.post('/api/reconciliation/start/', {
            'month': '2026-01', 'csv_content': csv,
        }, format='json')
        session = ReconciliationSession.objects.get(user=self.user, month='2026-01')
        # Ensure no unmatched entries remain (matcher should have matched it)
        session.entries.filter(status__in=['unmatched_app', 'unmatched_bank']).delete()
        res = self.client.post(f'/api/reconciliation/{session.id}/close/')
        self.assertEqual(res.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'closed')

    def test_cannot_close_other_users_session(self):
        _, other = auth_client('rec_close_other')
        session = ReconciliationSession.objects.create(user=other, month='2026-05', status='open')
        res = self.client.post(f'/api/reconciliation/{session.id}/close/')
        self.assertIn(res.status_code, [403, 404])
        session.refresh_from_db()
        self.assertEqual(session.status, 'open')
