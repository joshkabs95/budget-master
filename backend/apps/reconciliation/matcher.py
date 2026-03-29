"""
3-pass reconciliation matcher:
  Pass 1 — Exact:  same amount (cent-precise) + date within 1 day
  Pass 2 — Fuzzy:  amount within 0.50€ + date within 5 days + label similarity ≥ 0.40
  Pass 3 — Manual: remaining unmatched presented to the user
"""
from datetime import timedelta
from decimal import Decimal
import re


def _normalize(s: str) -> str:
    """Lower, strip accents-ish, keep alphanum."""
    s = s.lower().strip()
    replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a', 'ô': 'o', 'ù': 'u', 'î': 'i', 'ç': 'c'}
    for k, v in replacements.items():
        s = s.replace(k, v)
    return re.sub(r'[^a-z0-9 ]', ' ', s)


def _token_similarity(a: str, b: str) -> float:
    """Jaccard similarity on word tokens."""
    ta = set(_normalize(a).split())
    tb = set(_normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match(app_transactions, bank_lines):
    """
    app_transactions: list of Transaction objects
    bank_lines: list of dicts {'date': date, 'label': str, 'amount': Decimal}

    Returns list of dicts:
      {
        'transaction': Transaction | None,
        'bank_date': date | None,
        'bank_label': str,
        'bank_amount': Decimal | None,
        'status': 'auto' | 'manual' | 'unmatched_app' | 'unmatched_bank',
        'match_score': float,
      }
    """
    results = []
    used_txn = set()   # indices into app_transactions
    used_bank = set()  # indices into bank_lines

    # ── Pass 1: Exact ──────────────────────────────────────────────
    for bi, bank in enumerate(bank_lines):
        b_amount = abs(bank['amount'])
        b_date = bank['date']
        for ti, txn in enumerate(app_transactions):
            if ti in used_txn:
                continue
            t_amount = abs(txn.amount)
            date_diff = abs((b_date - txn.date).days)
            if t_amount == b_amount and date_diff <= 1:
                results.append({
                    'transaction': txn,
                    'bank_date': bank['date'],
                    'bank_label': bank['label'],
                    'bank_amount': bank['amount'],
                    'status': 'auto',
                    'match_score': 1.0,
                })
                used_txn.add(ti)
                used_bank.add(bi)
                break

    # ── Pass 2: Fuzzy ──────────────────────────────────────────────
    for bi, bank in enumerate(bank_lines):
        if bi in used_bank:
            continue
        b_amount = abs(bank['amount'])
        b_date = bank['date']
        best_score, best_ti = 0.0, None
        for ti, txn in enumerate(app_transactions):
            if ti in used_txn:
                continue
            t_amount = abs(txn.amount)
            date_diff = abs((b_date - txn.date).days)
            if abs(float(t_amount) - float(b_amount)) > 0.50 or date_diff > 5:
                continue
            label_sim = _token_similarity(bank['label'], txn.label)
            # Score = label similarity weighted by amount proximity and date proximity
            amount_score = max(0, 1 - abs(float(t_amount) - float(b_amount)) / 0.50)
            date_score = max(0, 1 - date_diff / 5)
            score = 0.5 * label_sim + 0.3 * amount_score + 0.2 * date_score
            if score > best_score and score >= 0.40:
                best_score = score
                best_ti = ti
        if best_ti is not None:
            txn = app_transactions[best_ti]
            results.append({
                'transaction': txn,
                'bank_date': bank['date'],
                'bank_label': bank['label'],
                'bank_amount': bank['amount'],
                'status': 'auto',
                'match_score': round(best_score, 3),
            })
            used_txn.add(best_ti)
            used_bank.add(bi)

    # ── Pass 3: Unmatched ──────────────────────────────────────────
    for bi, bank in enumerate(bank_lines):
        if bi in used_bank:
            continue
        results.append({
            'transaction': None,
            'bank_date': bank['date'],
            'bank_label': bank['label'],
            'bank_amount': bank['amount'],
            'status': 'unmatched_bank',
            'match_score': 0.0,
        })

    for ti, txn in enumerate(app_transactions):
        if ti in used_txn:
            continue
        results.append({
            'transaction': txn,
            'bank_date': None,
            'bank_label': '',
            'bank_amount': None,
            'status': 'unmatched_app',
            'match_score': 0.0,
        })

    return results
