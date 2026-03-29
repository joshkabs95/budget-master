import hashlib
import re

AUTO_RULES = {
    "Alimentation": {
        "keywords": ["carrefour", "auchan", "leclerc", "lidl", "monoprix", "restaurant", "mcdo", "kfc", "uber eats", "deliveroo", "casino", "intermarché", "franprix"],
        "icon": "🛒", "color": "#22c55e", "rule_bucket": "needs"
    },
    "Logement": {
        "keywords": ["loyer", "edf", "gdf", "eau", "charges", "syndic", "assurance habitation", "engie", "veolia"],
        "icon": "🏠", "color": "#3b82f6", "rule_bucket": "needs"
    },
    "Transport": {
        "keywords": ["sncf", "ratp", "uber", "essence", "total", "bp", "parking", "péage", "vinci", "blablacar", "navigo"],
        "icon": "🚗", "color": "#f97316", "rule_bucket": "needs"
    },
    "Loisirs": {
        "keywords": ["netflix", "spotify", "amazon", "fnac", "cinema", "steam", "playstation", "apple", "disney", "deezer"],
        "icon": "🎬", "color": "#a855f7", "rule_bucket": "wants"
    },
    "Services": {
        "keywords": ["sfr", "orange", "bouygues", "free", "assurance", "mutuelle", "abonnement"],
        "icon": "📱", "color": "#6b6b7e", "rule_bucket": "needs"
    },
    "Revenus": {
        "keywords": ["salaire", "virement", "caf", "remboursement", "prime", "freelance", "allocation"],
        "icon": "💰", "color": "#22c55e", "rule_bucket": "needs"
    },
    "Épargne": {
        "keywords": ["livret a", "pel", "pea", "assurance vie", "virement épargne", "ldds"],
        "icon": "🏦", "color": "#3b82f6", "rule_bucket": "savings"
    },
}


def categorize_label(label: str, user=None) -> dict:
    """
    Returns best matching category info dict or None.
    Checks user-defined CategoryRules first, then falls back to AUTO_RULES.
    """
    label_lower = label.lower().strip()

    # ── 1. User-defined rules (highest priority) ─────────────────────────────
    if user is not None:
        try:
            from apps.categories.models import CategoryRule
            for rule in CategoryRule.objects.filter(user=user).select_related('category').order_by('-priority', 'keyword'):
                if rule.keyword.lower() in label_lower:
                    cat = rule.category
                    return {
                        "name": cat.name,
                        "icon": cat.icon,
                        "color": cat.color,
                        "rule_bucket": cat.rule_bucket,
                        "confidence": 1.0,
                        "category_id": cat.id,
                    }
        except Exception:
            pass

    # ── 2. Generic AUTO_RULES fallback ────────────────────────────────────────
    best_match = None
    best_score = 0

    for cat_name, cat_data in AUTO_RULES.items():
        for keyword in cat_data["keywords"]:
            if keyword in label_lower:
                score = len(keyword) / len(label_lower)
                if score > best_score:
                    best_score = score
                    best_match = {"name": cat_name, **cat_data, "confidence": round(score, 2)}

    return best_match


def compute_import_hash(date: str, amount: str, label: str) -> str:
    """Anti-duplicate hash: hash(date + amount + normalized_label)."""
    normalized = re.sub(r'\s+', ' ', label.lower().strip())
    raw = f"{date}|{amount}|{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()
