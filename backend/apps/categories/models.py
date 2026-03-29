import re
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings


def validate_month(value):
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', value):
        raise ValidationError(f'"{value}" n\'est pas un format de mois valide (YYYY-MM).')


class Category(models.Model):
    RULE_BUCKET_CHOICES = [
        ('needs', 'Besoins'),
        ('wants', 'Envies'),
        ('savings', 'Épargne'),
    ]
    TYPE_CHOICES = [
        ('income', 'Revenu'),
        ('expense', 'Dépense'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📦')
    color = models.CharField(max_length=7, default='#6b6b7e')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='expense')
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rule_bucket = models.CharField(max_length=10, choices=RULE_BUCKET_CHOICES, default='wants')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'rule_bucket'], name='idx_cat_user_bucket'),
            models.Index(fields=['user', 'type'], name='idx_cat_user_type'),
        ]

    def __str__(self):
        return f"{self.icon} {self.name}"


class CategoryRule(models.Model):
    """Règle d'auto-catégorisation définie par l'utilisateur.
    Si le libellé d'une transaction contient `keyword` (insensible à la casse),
    la catégorie est assignée automatiquement à l'import.
    """
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='category_rules')
    keyword  = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='rules')
    priority = models.PositiveSmallIntegerField(default=0, help_text="Plus élevé = prioritaire")

    class Meta:
        db_table = 'category_rules'
        ordering = ['-priority', 'keyword']
        unique_together = ['user', 'keyword']

    def __str__(self):
        return f'"{self.keyword}" → {self.category.name}'


class CategoryBudget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='category_budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    month = models.CharField(max_length=7, validators=[validate_month])  # YYYY-MM
    allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    carried_over = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'category_budgets'
        unique_together = ['user', 'category', 'month']
        ordering = ['category__name']

    def __str__(self):
        return f"{self.user} — {self.category} — {self.month}"
