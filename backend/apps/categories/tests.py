"""
Tests — Category model + merge + API + CategoryRule
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.categories.models import Category, CategoryRule, CategoryBudget

User = get_user_model()


def make_user(username='cat_user', password='testpass123'):
    return User.objects.create_user(username=username, password=password)


def make_category(user, name='Test', **kwargs):
    defaults = dict(icon='📦', color='#aaa', type='expense', rule_bucket='needs')
    defaults.update(kwargs)
    return Category.objects.create(user=user, name=name, **defaults)


def auth_client(username, password='testpass123'):
    user = User.objects.create_user(username=username, password=password)
    client = APIClient()
    res = client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client, user


# ─── Model ──────────────────────────────────────────────────────────────────

class CategoryModelTest(TestCase):

    def setUp(self):
        self.user = make_user('cat_model')

    def test_create_category(self):
        c = make_category(self.user, name='Loyer')
        self.assertEqual(str(c), '📦 Loyer')

    def test_isolation_between_users(self):
        u2 = make_user('cat_model2')
        make_category(self.user, name='Mine')
        make_category(u2, name='Pas à moi')
        my_names = list(Category.objects.filter(user=self.user).values_list('name', flat=True))
        other_names = list(Category.objects.filter(user=u2).values_list('name', flat=True))
        self.assertIn('Mine', my_names)
        self.assertNotIn('Pas à moi', my_names)
        self.assertIn('Pas à moi', other_names)
        self.assertNotIn('Mine', other_names)

    def test_budget_month_validation(self):
        from django.core.exceptions import ValidationError
        c = make_category(self.user)
        b = CategoryBudget(user=self.user, category=c, month='2026-13', allocated=100)
        with self.assertRaises(ValidationError):
            b.full_clean()

    def test_budget_valid_month(self):
        from django.core.exceptions import ValidationError
        c = make_category(self.user)
        b = CategoryBudget(user=self.user, category=c, month='2026-06', allocated=100)
        try:
            b.full_clean()
        except ValidationError:
            self.fail('valid month raised ValidationError')


# ─── Merge ──────────────────────────────────────────────────────────────────

class CategoryMergeTest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('cat_merge')

    def test_merge_reassigns_transactions(self):
        from apps.transactions.models import Transaction
        source = make_category(self.user, name='Source')
        target = make_category(self.user, name='Target')
        t = Transaction.objects.create(
            user=self.user, label='tx', amount=Decimal('10'), type='expense',
            date=date.today(), category=source
        )
        res = self.client.post(f'/api/categories/{source.id}/merge_into/', {'target_id': target.id}, format='json')
        self.assertEqual(res.status_code, 200)
        t.refresh_from_db()
        self.assertEqual(t.category_id, target.id)
        self.assertFalse(Category.objects.filter(pk=source.id).exists())

    def test_merge_returns_count(self):
        from apps.transactions.models import Transaction
        source = make_category(self.user, name='S')
        target = make_category(self.user, name='T')
        for i in range(3):
            Transaction.objects.create(
                user=self.user, label=f'tx{i}', amount=Decimal('5'), type='expense',
                date=date.today(), category=source
            )
        res = self.client.post(f'/api/categories/{source.id}/merge_into/', {'target_id': target.id}, format='json')
        self.assertEqual(res.data['merged'], 3)
        self.assertEqual(res.data['target'], 'T')

    def test_merge_same_source_target_returns_400(self):
        c = make_category(self.user, name='Self')
        res = self.client.post(f'/api/categories/{c.id}/merge_into/', {'target_id': c.id}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_merge_missing_target_id_returns_400(self):
        c = make_category(self.user, name='NoTarget')
        res = self.client.post(f'/api/categories/{c.id}/merge_into/', {}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_cannot_merge_other_users_category(self):
        _, other = auth_client('cat_merge_other')
        other_source = make_category(other, name='OtherSource')
        target = make_category(self.user, name='MyTarget')
        res = self.client.post(f'/api/categories/{other_source.id}/merge_into/', {'target_id': target.id}, format='json')
        self.assertIn(res.status_code, [403, 404])


# ─── CategoryRule ───────────────────────────────────────────────────────────

class CategoryRuleAPITest(TestCase):

    def setUp(self):
        self.client, self.user = auth_client('rule_user')
        self.cat = make_category(self.user, name='Alimentation')

    def test_create_rule(self):
        res = self.client.post('/api/category-rules/', {
            'keyword': 'carrefour', 'category': self.cat.id, 'priority': 0
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(CategoryRule.objects.filter(user=self.user, keyword='carrefour').exists())

    def test_list_rules(self):
        CategoryRule.objects.create(user=self.user, keyword='lidl', category=self.cat)
        res = self.client.get('/api/category-rules/')
        self.assertEqual(res.status_code, 200)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 1)

    def test_delete_rule(self):
        r = CategoryRule.objects.create(user=self.user, keyword='auchan', category=self.cat)
        res = self.client.delete(f'/api/category-rules/{r.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(CategoryRule.objects.filter(pk=r.id).exists())

    def test_isolation_between_users(self):
        _, other = auth_client('rule_other')
        other_cat = make_category(other, name='OtherCat')
        CategoryRule.objects.create(user=other, keyword='secret', category=other_cat)
        res = self.client.get('/api/category-rules/')
        results = res.data.get('results', res.data)
        keywords = [r['keyword'] for r in results]
        self.assertNotIn('secret', keywords)
