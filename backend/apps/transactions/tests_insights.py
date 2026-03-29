"""
Tests unitaires — generate_insights (transactions/services/insights.py)
"""
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from django.test import TestCase


class InsightsTest(TestCase):
    """Smoke tests: insights returns a list and doesn't crash."""

    def test_insights_returns_list_for_user_without_data(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='test_insights', password='x')
        from apps.transactions.services.insights import generate_insights
        result = generate_insights(user)
        self.assertIsInstance(result, list)

    def test_insights_no_crash_no_transactions(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='test_insights2', password='x')
        from apps.transactions.services.insights import generate_insights
        try:
            generate_insights(user)
        except Exception as e:
            self.fail(f"generate_insights raised {e}")
