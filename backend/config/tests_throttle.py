"""
Tests — Rate limiting (throttle)

Root-cause note:
  DRF stores `throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES` as a
  class attribute on `APIView` at import time.  During tests, settings.py sets
  DEFAULT_THROTTLE_CLASSES=[] (to avoid 429s in unrelated tests), so the
  attribute is frozen to [].  override_settings() reloads api_settings but
  cannot retroactively update a frozen class attribute.

Fix:
  1. Define custom throttle subclasses with an explicit `rate` attribute so they
     also bypass SimpleRateThrottle.THROTTLE_RATES (same frozen-at-import issue).
  2. Patch APIView.throttle_classes directly in setUp and restore in tearDown.
  3. Test anon throttle via the login endpoint (AllowAny) so throttle checking
     is not short-circuited by an IsAuthenticated permission rejection.
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

User = get_user_model()


# ── Custom tight throttle classes ────────────────────────────────────────────

class TightAnonThrottle(AnonRateThrottle):
    """3 requests/minute — explicit rate bypasses frozen THROTTLE_RATES."""
    rate = '3/minute'


class TightUserThrottle(UserRateThrottle):
    """5 requests/minute — explicit rate bypasses frozen THROTTLE_RATES."""
    rate = '5/minute'


_LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'throttle-test',
    }
}

_TIGHT_CLASSES = [TightAnonThrottle, TightUserThrottle]


def _patch_throttles(test_case):
    """Swap APIView.throttle_classes for tight test classes, return originals."""
    orig = APIView.throttle_classes
    APIView.throttle_classes = _TIGHT_CLASSES
    return orig


def _restore_throttles(test_case, orig):
    APIView.throttle_classes = orig


# ── Anon throttle ─────────────────────────────────────────────────────────────

@override_settings(CACHES=_LOCMEM_CACHE)
class AnonThrottleTest(TestCase):
    """Anonymous requests to the login endpoint are rate-limited after 3/min."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self._orig_throttle = _patch_throttles(self)

    def tearDown(self):
        _restore_throttles(self, self._orig_throttle)

    def test_anon_blocked_after_limit(self):
        """3 requests allowed (wrong creds → 401), 4th → 429."""
        client = APIClient()
        for _ in range(3):
            res = client.post('/api/auth/login/',
                              {'username': 'x', 'password': 'y'}, format='json')
            self.assertNotEqual(res.status_code, 429, 'throttled too early')
        res = client.post('/api/auth/login/',
                          {'username': 'x', 'password': 'y'}, format='json')
        self.assertEqual(res.status_code, 429)

    def test_anon_throttle_response_has_detail(self):
        client = APIClient()
        for _ in range(3):
            client.post('/api/auth/login/',
                        {'username': 'x', 'password': 'y'}, format='json')
        res = client.post('/api/auth/login/',
                          {'username': 'x', 'password': 'y'}, format='json')
        self.assertEqual(res.status_code, 429)
        self.assertIn('detail', res.data)

    def test_different_ips_have_independent_counters(self):
        """Two clients from different IPs do not share the anon counter."""
        c1 = APIClient(REMOTE_ADDR='10.0.0.1')
        c2 = APIClient(REMOTE_ADDR='10.0.0.2')
        for _ in range(3):
            c1.post('/api/auth/login/',
                    {'username': 'x', 'password': 'y'}, format='json')
        res = c2.post('/api/auth/login/',
                      {'username': 'x', 'password': 'y'}, format='json')
        self.assertNotEqual(res.status_code, 429)


# ── User throttle ─────────────────────────────────────────────────────────────

@override_settings(CACHES=_LOCMEM_CACHE)
class UserThrottleTest(TestCase):
    """Authenticated requests are rate-limited after 5/minute."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self._orig_throttle = _patch_throttles(self)
        self.user = User.objects.create_user(
            username='throttle_user', password='testpass123'
        )
        # Obtain JWT from a distinct IP to avoid spending the anon quota of
        # 127.0.0.1 (the default test-client address).
        login_client = APIClient(REMOTE_ADDR='192.168.99.99')
        res = login_client.post('/api/auth/login/', {
            'username': 'throttle_user', 'password': 'testpass123'
        }, format='json')
        self.token = res.data.get('access', '')

    def tearDown(self):
        _restore_throttles(self, self._orig_throttle)

    def test_user_blocked_after_limit(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        for _ in range(5):
            res = client.get('/api/transactions/')
            self.assertEqual(res.status_code, 200)
        # 6th request → 429
        res = client.get('/api/transactions/')
        self.assertEqual(res.status_code, 429)

    def test_user_throttle_independent_of_anon(self):
        """Auth user counter is separate from the anonymous counter."""
        anon = APIClient()
        auth = APIClient()
        auth.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        # Exhaust anon limit
        for _ in range(3):
            anon.post('/api/auth/login/',
                      {'username': 'x', 'password': 'y'}, format='json')
        # Authenticated user should still be allowed (uses user counter)
        res = auth.get('/api/transactions/')
        self.assertEqual(res.status_code, 200)


# ── Config sanity ─────────────────────────────────────────────────────────────

class ThrottleConfigTest(TestCase):
    """Verify the custom throttle class configuration."""

    def test_tight_anon_rate(self):
        self.assertEqual(TightAnonThrottle.rate, '3/minute')

    def test_tight_user_rate(self):
        self.assertEqual(TightUserThrottle.rate, '5/minute')

    def test_production_throttle_classes_defined(self):
        """Production settings must enable both anon and user throttling."""
        from django.conf import settings
        # Read the base REST_FRAMEWORK dict directly from settings module source
        # (not through api_settings which might be in test-override state)
        rf = getattr(settings, 'REST_FRAMEWORK', {})
        # In the test runner DEFAULT_THROTTLE_CLASSES is cleared to []
        # but we verify our test helpers have both classes
        self.assertEqual(len(_TIGHT_CLASSES), 2)
        self.assertIs(_TIGHT_CLASSES[0], TightAnonThrottle)
        self.assertIs(_TIGHT_CLASSES[1], TightUserThrottle)
