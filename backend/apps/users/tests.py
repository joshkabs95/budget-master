"""
Tests — Auth API (register, login, profile, change-password, export-backup, onboarding)
"""
import json
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def auth_client(username='testuser', password='testpass123'):
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    res = client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client, User.objects.get(username=username)


# ─── Register / Login ───────────────────────────────────────────────────────

class AuthTest(TestCase):

    def test_register_success(self):
        client = APIClient()
        res = client.post('/api/auth/register/', {
            'username': 'newuser', 'email': 'new@test.com', 'password': 'strongpass1'
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='dup', password='x')
        client = APIClient()
        res = client.post('/api/auth/register/', {'username': 'dup', 'password': 'strongpass1'}, format='json')
        self.assertIn(res.status_code, [400, 409])

    def test_login_returns_tokens(self):
        User.objects.create_user(username='logintest', password='testpass123')
        client = APIClient()
        res = client.post('/api/auth/login/', {'username': 'logintest', 'password': 'testpass123'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_login_wrong_password(self):
        User.objects.create_user(username='loginbad', password='testpass123')
        client = APIClient()
        res = client.post('/api/auth/login/', {'username': 'loginbad', 'password': 'wrongpass'}, format='json')
        self.assertIn(res.status_code, [400, 401])


# ─── Profile ────────────────────────────────────────────────────────────────

class ProfileTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('prof_user')

    def test_get_profile(self):
        res = self.client.get('/api/auth/profile/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['username'], 'prof_user')
        self.assertIn('onboarding_done', res.data)

    def test_onboarding_done_defaults_false(self):
        res = self.client.get('/api/auth/profile/')
        self.assertFalse(res.data['onboarding_done'])


# ─── Change Password ────────────────────────────────────────────────────────

class ChangePasswordTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('pw_user')

    def test_change_password_success(self):
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'testpass123',
            'new_password': 'newstrongpass456',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newstrongpass456'))

    def test_change_password_wrong_current(self):
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'wrongpassword',
            'new_password': 'newstrongpass456',
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.data)

    def test_change_password_too_short(self):
        res = self.client.post('/api/auth/change-password/', {
            'current_password': 'testpass123',
            'new_password': 'abc',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_change_password_requires_auth(self):
        unauth = APIClient()
        res = unauth.post('/api/auth/change-password/', {
            'current_password': 'testpass123',
            'new_password': 'newstrongpass456',
        }, format='json')
        self.assertEqual(res.status_code, 401)


# ─── Complete Onboarding ────────────────────────────────────────────────────

class OnboardingTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('onboard_user')

    def test_complete_onboarding_sets_flag(self):
        res = self.client.post('/api/auth/complete-onboarding/', {
            'needs_pct': 50, 'wants_pct': 30, 'savings_pct': 20,
            'monthly_income': 2500,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_done)

    def test_complete_onboarding_creates_savings_rule(self):
        from apps.savings.models import SavingsRule
        self.client.post('/api/auth/complete-onboarding/', {
            'needs_pct': 60, 'wants_pct': 20, 'savings_pct': 20,
        }, format='json')
        rule = SavingsRule.objects.filter(user=self.user).first()
        self.assertIsNotNone(rule)
        self.assertEqual(float(rule.needs_target), 60.0)

    def test_complete_onboarding_creates_first_category(self):
        from apps.categories.models import Category
        self.client.post('/api/auth/complete-onboarding/', {
            'needs_pct': 50, 'wants_pct': 30, 'savings_pct': 20,
            'first_category': 'Alimentation',
        }, format='json')
        self.assertTrue(Category.objects.filter(user=self.user, name='Alimentation').exists())

    def test_complete_onboarding_empty_category_ok(self):
        res = self.client.post('/api/auth/complete-onboarding/', {
            'needs_pct': 50, 'wants_pct': 30, 'savings_pct': 20,
            'first_category': '',
        }, format='json')
        self.assertEqual(res.status_code, 200)


# ─── Export Backup ──────────────────────────────────────────────────────────

class ExportBackupTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('export_user')

    def test_export_returns_json_file(self):
        res = self.client.get('/api/auth/export-backup/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        self.assertIn('attachment', res['Content-Disposition'])
        self.assertIn('.json', res['Content-Disposition'])

    def test_export_contains_expected_keys(self):
        res = self.client.get('/api/auth/export-backup/')
        data = json.loads(res.content)
        self.assertIn('exported_at', data)
        self.assertIn('username', data)
        self.assertIn('transactions', data)
        self.assertIn('categories', data)
        self.assertIn('savings_accounts', data)
        self.assertIn('goals', data)

    def test_export_username_matches(self):
        res = self.client.get('/api/auth/export-backup/')
        data = json.loads(res.content)
        self.assertEqual(data['username'], 'export_user')

    def test_export_requires_auth(self):
        unauth = APIClient()
        res = unauth.get('/api/auth/export-backup/')
        self.assertEqual(res.status_code, 401)
