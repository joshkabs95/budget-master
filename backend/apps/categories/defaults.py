"""
Catégories par défaut créées automatiquement pour chaque nouvel utilisateur.
"""

DEFAULT_CATEGORIES = [
    # (nom, bucket, icône, type)
    # ── Needs ──────────────────────────────────────────────────────────
    ('Logement',       'needs',   '🏠', 'expense'),
    ('Énergie',        'needs',   '⚡', 'expense'),
    ('Crédit',         'needs',   '💳', 'expense'),
    ('Alimentation',   'needs',   '🛒', 'expense'),
    ('Transport',      'needs',   '⛽', 'expense'),
    ('Santé',          'needs',   '💊', 'expense'),
    ('Téléphonie',     'needs',   '📞', 'expense'),
    ('Assurances',     'needs',   '🛡️', 'expense'),
    ('Formation',      'needs',   '🎓', 'expense'),
    ('Enfants',        'needs',   '👶', 'expense'),
    ('Salaire',        'needs',   '💼', 'income'),
    # ── Wants ──────────────────────────────────────────────────────────
    ('Loisirs',        'wants',   '🎬', 'expense'),
    ('Sorties',        'wants',   '🍽️', 'expense'),
    ('Shopping',       'wants',   '👗', 'expense'),
    ('Abonnements',    'wants',   '📱', 'expense'),
    ('Bien-être',      'wants',   '💆', 'expense'),
    ('Voyages',        'wants',   '✈️', 'expense'),
    ('Cadeaux / Dons', 'wants',   '🎁', 'expense'),
    # ── Savings ────────────────────────────────────────────────────────
    ('Épargne',        'savings', '💰', 'expense'),
    ('Investissement', 'savings', '📈', 'expense'),
]


def create_default_categories(user):
    """Crée les catégories par défaut pour un utilisateur (idempotent)."""
    from .models import Category
    existing = set(Category.objects.filter(user=user).values_list('name', flat=True))
    to_create = [
        Category(user=user, name=nom, rule_bucket=bucket, icon=icon, type=ctype)
        for nom, bucket, icon, ctype in DEFAULT_CATEGORIES
        if nom not in existing
    ]
    if to_create:
        Category.objects.bulk_create(to_create, ignore_conflicts=True)
    return len(to_create)
