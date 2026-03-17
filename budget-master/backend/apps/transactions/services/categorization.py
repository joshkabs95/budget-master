AUTO_RULES = {
    "Alimentation": ["carrefour", "auchan", "leclerc", "lidl", "monoprix", "restaurant", "mcdo", "kfc", "uber eats", "deliveroo"],
    "Logement": ["loyer", "edf", "gdf", "eau", "charges", "syndic", "assurance habitation"],
    "Transport": ["sncf", "ratp", "uber", "essence", "total", "bp", "parking", "péage", "vinci", "blablacar"],
    "Loisirs": ["netflix", "spotify", "amazon", "fnac", "cinema", "steam", "playstation", "apple"],
    "Services": ["sfr", "orange", "bouygues", "free", "assurance", "mutuelle", "abonnement"],
    "Revenus": ["salaire", "virement", "caf", "remboursement", "prime", "freelance"],
    "Épargne": ["livret a", "pel", "pea", "assurance vie", "virement épargne", "ldds"],
}


def auto_categorize(label: str, user) -> tuple:
    """Returns (category_name, confidence_score)"""
    label_lower = label.lower()
    for cat_name, keywords in AUTO_RULES.items():
        for kw in keywords:
            if kw in label_lower:
                return cat_name, 0.9
    return "Autre", 0.0


def compute_import_hash(date, amount, label) -> str:
    import hashlib
    key = f"{date}|{amount}|{label.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()
