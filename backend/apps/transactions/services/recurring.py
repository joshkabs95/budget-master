"""
Détection automatique des transactions récurrentes.

Algorithme :
- Normalise le libellé (supprime dates, montants, refs)
- Groupe par (libellé_normalisé, catégorie, type)
- Si le groupe apparaît dans ≥ 2 des 3 derniers mois
  ET variance de montant ≤ 40% → considéré récurrent
"""
import re
from datetime import date
from collections import defaultdict


def _normalize(label: str) -> str:
    label = re.sub(r'\d{2}[./]\d{2}([./]\d{2,4})?', '', label)   # dates
    label = re.sub(r'#[A-Za-z0-9]+', '', label)                   # refs hex
    label = re.sub(r'\b\d{5,}\b', '', label)                      # long numbers
    label = re.sub(r'\(\d+\)', '', label)                          # (1), (2) suffixes
    label = re.sub(r'\s+', ' ', label).strip().lower()
    return label[:50]


def detect_recurring(user) -> list:
    """
    Retourne la liste des patterns récurrents détectés sur les 3 derniers mois.
    Chaque entrée : {label, category, type, avg_amount, months_seen, frequency, confidence}
    """
    from apps.transactions.models import Transaction

    today = date.today()
    groups = defaultdict(list)

    for i in range(1, 4):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12; y -= 1

        txns = Transaction.objects.filter(
            user=user, date__year=y, date__month=m,
            type__in=['expense', 'income'],
        ).select_related('category')

        for t in txns:
            key = (_normalize(t.label), t.category_id, t.type)
            groups[key].append({
                'month': f'{y}-{m:02d}',
                'amount': float(t.amount),
                'label': t.label,
                'category_name': t.category.name if t.category else '',
                'category_icon': t.category.icon if t.category else '',
            })

    results = []
    for (norm_label, cat_id, txn_type), entries in groups.items():
        months_seen = len(set(e['month'] for e in entries))
        if months_seen < 2:
            continue

        amounts = [e['amount'] for e in entries]
        avg = sum(amounts) / len(amounts)

        # Reject if too variable (> 40% deviation from average)
        if avg > 0:
            max_dev = max(abs(a - avg) / avg for a in amounts)
            if max_dev > 0.40:
                continue

        # Confidence: 3 months = high, 2 months = medium
        confidence = 'high' if months_seen == 3 else 'medium'

        last = sorted(entries, key=lambda e: e['month'], reverse=True)[0]
        results.append({
            'label': last['label'],
            'category': last['category_name'],
            'category_icon': last['category_icon'],
            'type': txn_type,
            'avg_amount': round(avg, 2),
            'months_seen': months_seen,
            'frequency': 'monthly',
            'confidence': confidence,
        })

    results.sort(key=lambda r: r['avg_amount'], reverse=True)
    return results[:25]
