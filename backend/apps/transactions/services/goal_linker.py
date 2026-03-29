"""
Goal auto-linker service.

Scores each Goal against a Transaction label using keyword matching.
Only eligible transactions (type=saving or savings-bucket expenses) are considered.

Score = len(matching_keyword) / len(label)  — same pattern as categorization.
Minimum threshold: 0.10
"""
import re


def _keywords(text: str) -> list:
    """Lowercase, split on separators, return tokens >= 3 chars."""
    tokens = re.split(r"[\s\-_/']+", text.lower().strip())
    return [t for t in tokens if len(t) >= 3]


def _score(label: str, goal_name: str) -> float:
    label_lower = label.lower()
    best = 0.0
    for kw in _keywords(goal_name):
        if kw in label_lower:
            s = len(kw) / max(len(label_lower), 1)
            if s > best:
                best = s
    return best


_SAVINGS_KW = {'epargne', 'saving', 'virement', 'livret', 'invest', 'projet'}


def _is_eligible(txn) -> bool:
    """Exclude pure income. Allow saving-type and expenses that look like savings."""
    if txn.type == 'income':
        return False
    if txn.type == 'saving':
        return True
    # expense: allow if label contains a savings keyword OR category is savings bucket
    label_lower = txn.label.lower()
    if any(kw in label_lower for kw in _SAVINGS_KW):
        return True
    if txn.category and txn.category.rule_bucket == 'savings':
        return True
    return False


def find_best_goal(txn):
    """Return the best-matching Goal for txn, or None."""
    from apps.goals.models import Goal

    MIN_SCORE = 0.10

    if not _is_eligible(txn):
        return None

    best_goal = None
    best_score = MIN_SCORE

    for goal in Goal.objects.filter(user=txn.user):
        s = _score(txn.label, goal.name)
        if s > best_score:
            best_score = s
            best_goal = goal

    return best_goal
