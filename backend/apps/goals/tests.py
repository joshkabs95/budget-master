"""
Tests — Goal model (properties + API)
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.goals.models import Goal

User = get_user_model()


def make_user(username='goal_user', password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def make_goal(user, **kwargs):
    defaults = dict(
        name='Vacances',
        type='savings',
        target_amount=Decimal('1000.00'),
        current_amount=Decimal('0.00'),
        deadline=date.today() + timedelta(days=180),
    )
    defaults.update(kwargs)
    return Goal.objects.create(user=user, **defaults)


# ─── Properties ─────────────────────────────────────────────────────────────

class GoalPropertiesTest(TestCase):

    def setUp(self):
        self.user = make_user('goal_props')

    def test_progress_zero_when_empty(self):
        g = make_goal(self.user, current_amount=Decimal('0'))
        self.assertEqual(g.progress, 0.0)

    def test_progress_50_percent(self):
        g = make_goal(self.user, target_amount=Decimal('1000'), current_amount=Decimal('500'))
        self.assertAlmostEqual(g.progress, 50.0, places=1)

    def test_progress_100_percent(self):
        g = make_goal(self.user, target_amount=Decimal('500'), current_amount=Decimal('500'))
        self.assertAlmostEqual(g.progress, 100.0, places=1)

    def test_progress_over_100(self):
        g = make_goal(self.user, target_amount=Decimal('100'), current_amount=Decimal('150'))
        self.assertAlmostEqual(g.progress, 150.0, places=1)

    def test_progress_zero_target_returns_zero(self):
        g = make_goal(self.user, target_amount=Decimal('0'), current_amount=Decimal('0'))
        self.assertEqual(g.progress, 0.0)

    def test_horizon_short(self):
        g = make_goal(self.user, deadline=date.today() + timedelta(days=30))
        self.assertEqual(g.horizon, 'short')

    def test_horizon_medium(self):
        g = make_goal(self.user, deadline=date.today() + timedelta(days=200))
        self.assertEqual(g.horizon, 'medium')

    def test_horizon_long(self):
        g = make_goal(self.user, deadline=date.today() + timedelta(days=400))
        self.assertEqual(g.horizon, 'long')

    def test_monthly_required_positive(self):
        g = make_goal(
            self.user,
            target_amount=Decimal('1200'),
            current_amount=Decimal('0'),
            deadline=date.today() + timedelta(days=365),
        )
        # ~1200 / 12 months ≈ 100 €/mois
        self.assertGreater(g.monthly_required, 0)
        self.assertAlmostEqual(g.monthly_required, 100.0, delta=5.0)

    def test_monthly_required_zero_when_past_deadline(self):
        g = make_goal(self.user, deadline=date.today() - timedelta(days=1))
        self.assertEqual(g.monthly_required, 0.0)

    def test_monthly_required_zero_when_already_reached(self):
        g = make_goal(
            self.user,
            target_amount=Decimal('500'),
            current_amount=Decimal('500'),
            deadline=date.today() + timedelta(days=90),
        )
        self.assertEqual(g.monthly_required, 0.0)


# ─── API ────────────────────────────────────────────────────────────────────

class GoalAPITest(TestCase):

    def setUp(self):
        self.user = make_user('goal_api')
        self.client = APIClient()
        res = self.client.post('/api/auth/login/', {'username': 'goal_api', 'password': 'testpass123'}, format='json')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])

    def test_create_goal(self):
        payload = {
            'name': 'Voiture',
            'type': 'savings',
            'target_amount': '5000.00',
            'current_amount': '0.00',
            'deadline': str(date.today() + timedelta(days=365)),
        }
        res = self.client.post('/api/goals/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['name'], 'Voiture')
        self.assertIn('progress', res.data)
        self.assertIn('horizon', res.data)

    def test_contribute_increases_current_amount(self):
        g = make_goal(self.user, target_amount=Decimal('1000'), current_amount=Decimal('0'))
        res = self.client.post(f'/api/goals/{g.id}/contribute/', {'amount': '200'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        g.refresh_from_db()
        self.assertEqual(g.current_amount, Decimal('200.00'))

    def test_isolation_between_users(self):
        other = make_user('goal_other')
        make_goal(other, name='Objectif autre')
        res = self.client.get('/api/goals/')
        results = res.data.get('results', res.data)
        names = [g['name'] for g in results]
        self.assertNotIn('Objectif autre', names)

    def test_delete_goal(self):
        g = make_goal(self.user)
        res = self.client.delete(f'/api/goals/{g.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Goal.objects.filter(pk=g.id).exists())
