"""
Tests — Notification model + API (list, unread_count, mark_read, mark_all_read)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.notifications.models import Notification

User = get_user_model()


def auth_client(username, password='testpass123'):
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    res = client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client, User.objects.get(username=username)


def make_notif(user, **kwargs):
    defaults = dict(type='info', severity='green', message='Test notification', read=False)
    defaults.update(kwargs)
    return Notification.objects.create(user=user, **defaults)


# ─── Model ──────────────────────────────────────────────────────────────────

class NotificationModelTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('notif_model')

    def test_create_notification(self):
        n = make_notif(self.user, message='Budget dépassé', severity='red', type='budget_exceeded')
        self.assertIn('red', str(n))
        self.assertFalse(n.read)

    def test_default_read_is_false(self):
        n = make_notif(self.user)
        self.assertFalse(n.read)
        self.assertFalse(n.email_sent)


# ─── List + Isolation ───────────────────────────────────────────────────────

class NotificationListTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('notif_list')

    def test_list_empty(self):
        res = self.client.get('/api/notifications/')
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 0)

    def test_list_own_notifications(self):
        make_notif(self.user, message='Mon alerte')
        res = self.client.get('/api/notifications/')
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['message'], 'Mon alerte')

    def test_isolation_between_users(self):
        _, other = auth_client('notif_other')
        make_notif(other, message='Alerte autre utilisateur')
        make_notif(self.user, message='Ma notification')
        res = self.client.get('/api/notifications/')
        results = res.data.get('results', res.data)
        messages = [n['message'] for n in results]
        self.assertIn('Ma notification', messages)
        self.assertNotIn('Alerte autre utilisateur', messages)

    def test_unauthenticated_returns_401(self):
        res = APIClient().get('/api/notifications/')
        self.assertEqual(res.status_code, 401)


# ─── Unread Count ────────────────────────────────────────────────────────────

class UnreadCountTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('notif_count')

    def test_unread_count_zero(self):
        res = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 0)

    def test_unread_count_with_notifications(self):
        make_notif(self.user, read=False)
        make_notif(self.user, read=False)
        make_notif(self.user, read=True)
        res = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(res.data['count'], 2)


# ─── Mark Read ───────────────────────────────────────────────────────────────

class MarkReadTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('notif_read')

    def test_mark_read_single(self):
        n = make_notif(self.user, read=False)
        res = self.client.post(f'/api/notifications/{n.id}/mark_read/')
        self.assertEqual(res.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.read)

    def test_cannot_mark_other_users_notification(self):
        _, other = auth_client('notif_read_other')
        n = make_notif(other, read=False)
        res = self.client.post(f'/api/notifications/{n.id}/mark_read/')
        self.assertIn(res.status_code, [403, 404])
        n.refresh_from_db()
        self.assertFalse(n.read)

    def test_mark_all_read(self):
        make_notif(self.user, read=False)
        make_notif(self.user, read=False)
        make_notif(self.user, read=False)
        res = self.client.post('/api/notifications/mark_all_read/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.user, read=False).count(), 0)

    def test_mark_all_read_does_not_affect_other_users(self):
        _, other = auth_client('notif_markall_other')
        n_other = make_notif(other, read=False)
        make_notif(self.user, read=False)
        self.client.post('/api/notifications/mark_all_read/')
        n_other.refresh_from_db()
        self.assertFalse(n_other.read)

    def test_ordering_most_recent_first(self):
        from django.utils import timezone
        import time
        n1 = make_notif(self.user, message='Old')
        time.sleep(0.05)
        n2 = make_notif(self.user, message='New')
        res = self.client.get('/api/notifications/')
        results = res.data.get('results', res.data)
        self.assertEqual(results[0]['message'], 'New')
        self.assertEqual(results[1]['message'], 'Old')
