"""
Tests unitaires — ForecastEngine (forecasting/engine.py)
"""
from decimal import Decimal
from datetime import date
from django.test import TestCase


class ForecastEngineTest(TestCase):

    def _make_user(self, username='test_fc'):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(username=username, password='x')

    def test_engine_instantiates(self):
        from apps.forecasting.engine import ForecastEngine
        user = self._make_user('fc_init')
        engine = ForecastEngine(user)
        self.assertIsNotNone(engine)

    def test_project_returns_list(self):
        from apps.forecasting.engine import ForecastEngine
        user = self._make_user('fc_proj')
        engine = ForecastEngine(user)
        result = engine.project(1)
        self.assertIsInstance(result, list)

    def test_project_no_data_returns_empty_or_list(self):
        from apps.forecasting.engine import ForecastEngine
        user = self._make_user('fc_nodata')
        result = ForecastEngine(user).project(3)
        self.assertIsInstance(result, list)

    def test_monthly_history_returns_list(self):
        from apps.forecasting.engine import ForecastEngine
        user = self._make_user('fc_hist')
        result = ForecastEngine(user).monthly_history(6)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 6)

    def test_project_shape(self):
        """Each projected month must have the expected keys."""
        from apps.forecasting.engine import ForecastEngine
        from apps.categories.models import Category
        from apps.transactions.models import Transaction

        user = self._make_user('fc_shape')
        # Seed 2 income transactions so projection has data
        Transaction.objects.create(
            user=user, label='Salaire', type='income',
            amount=Decimal('2000'), date=date(2025, 1, 1),
        )
        Transaction.objects.create(
            user=user, label='Salaire', type='income',
            amount=Decimal('2100'), date=date(2025, 2, 1),
        )
        result = ForecastEngine(user).project(1)
        if result:
            month = result[0]
            for key in ('month', 'projected_income', 'projected_expenses', 'net'):
                self.assertIn(key, month, f"Missing key '{key}' in projection")
