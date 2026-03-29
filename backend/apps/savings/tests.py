"""
Tests unitaires — AdaptiveRuleEngine (savings/services/adaptive_rule.py)
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.savings.services.adaptive_rule import AdaptiveRuleEngine


def _make_rule(user, savings_target=20, needs_target=50, wants_target=30,
               savings_floor=15, needs_floor=40, wants_floor=10,
               catchup_max_months=3):
    rule = MagicMock()
    rule.savings_target = Decimal(str(savings_target))
    rule.needs_target   = Decimal(str(needs_target))
    rule.wants_target   = Decimal(str(wants_target))
    rule.savings_floor  = Decimal(str(savings_floor))
    rule.needs_floor    = Decimal(str(needs_floor))
    rule.wants_floor    = Decimal(str(wants_floor))
    rule.catchup_max_months = catchup_max_months
    rule.user = user
    return rule


class AdaptiveRuleEngineTest(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(username='test_adaptive', password='x')
        self.engine = AdaptiveRuleEngine()
        self.rule = _make_rule(self.user)

    # ── Green path ────────────────────────────────────────────────────────────

    def test_green_when_savings_at_target(self):
        rates = {'savings': 20.0, 'needs': 50.0, 'wants': 30.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertEqual(result['status'], 'green')
        self.assertIsNone(result['plan'])

    def test_green_when_savings_above_target(self):
        rates = {'savings': 25.0, 'needs': 45.0, 'wants': 30.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertEqual(result['status'], 'green')

    # ── Yellow / orange path (wants cut alone covers gap) ────────────────────

    def test_yellow_small_gap_wants_only(self):
        # savings=17, needs=50, wants=33 → gap=3, wants_margin=33-10=23 → cut=3
        rates = {'savings': 17.0, 'needs': 50.0, 'wants': 33.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertIn(result['status'], ('yellow', 'orange'))
        steps = result['plan']['steps']
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['lever'], 'wants')
        self.assertAlmostEqual(steps[0]['cut'], 3.0, places=1)

    def test_orange_large_gap_wants_only(self):
        # savings=12, needs=50, wants=38 → gap=8, wants_margin=28 → cut=8
        rates = {'savings': 12.0, 'needs': 50.0, 'wants': 38.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertEqual(result['status'], 'orange')
        steps = result['plan']['steps']
        self.assertEqual(steps[0]['lever'], 'wants')
        self.assertAlmostEqual(steps[0]['cut'], 8.0, places=1)
        self.assertEqual(result['plan']['uncoverable_gap'], 0)

    # ── Red path (needs must be touched) ─────────────────────────────────────

    def test_red_when_needs_cut_required(self):
        # savings=15 (gap=5), wants=10 (at floor, margin=0), needs=55 (margin=15, cut=5, residual=0)
        # → steps=[{lever:'needs',cut:5}], residual=0, severity=red
        rates = {'savings': 15.0, 'needs': 55.0, 'wants': 10.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertEqual(result['status'], 'red')
        levers = [s['lever'] for s in result['plan']['steps']]
        self.assertIn('needs', levers)

    # ── Critical path (uncoverable gap) ──────────────────────────────────────

    def test_critical_when_both_floors_hit(self):
        # savings=0, wants=10 (floor), needs=40 (floor) → 20% gap, can't cover
        rates = {'savings': 0.0, 'needs': 40.0, 'wants': 10.0}
        result = self.engine.compensate(self.rule, rates)
        self.assertEqual(result['status'], 'critical')
        self.assertGreater(result['plan']['uncoverable_gap'], 0)

    # ── Severity helper ───────────────────────────────────────────────────────

    def test_severity_critical_residual_gap(self):
        sev = self.engine._severity([], residual_gap=5, total_gap=10)
        self.assertEqual(sev, 'critical')

    def test_severity_red_needs_lever(self):
        steps = [{'lever': 'needs', 'cut': 3}]
        sev = self.engine._severity(steps, 0, 8)
        self.assertEqual(sev, 'red')

    def test_severity_orange_large_gap_wants_only(self):
        steps = [{'lever': 'wants', 'cut': 6}]
        sev = self.engine._severity(steps, 0, 6)
        self.assertEqual(sev, 'orange')

    def test_severity_yellow_small_gap(self):
        steps = [{'lever': 'wants', 'cut': 3}]
        sev = self.engine._severity(steps, 0, 3)
        self.assertEqual(sev, 'yellow')

    # ── Catchup months ────────────────────────────────────────────────────────

    def test_catchup_1_month_small_gap(self):
        self.assertEqual(self.engine._catchup_months(3, self.rule), 1)

    def test_catchup_2_months_medium_gap(self):
        self.assertEqual(self.engine._catchup_months(7, self.rule), 2)

    def test_catchup_3_months_large_gap(self):
        self.assertEqual(self.engine._catchup_months(15, self.rule), 3)
