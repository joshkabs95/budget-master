"""
Management command: backfill goal auto-linking for existing transactions.

Usage:
    python manage.py backfill_goal_links
    python manage.py backfill_goal_links --dry-run
    python manage.py backfill_goal_links --user-id 7
"""
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction


class Command(BaseCommand):
    help = 'Backfill goal auto-linking for transactions without a linked goal.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--user-id', type=int, default=None, help='Restrict to one user')

    def handle(self, *args, **options):
        from apps.transactions.models import Transaction
        from apps.transactions.services.goal_linker import find_best_goal
        from apps.goals.models import Goal

        dry_run = options['dry_run']
        qs = Transaction.objects.filter(goal__isnull=True).select_related('category', 'user')
        if options['user_id']:
            qs = qs.filter(user_id=options['user_id'])

        linked = skipped = 0
        for txn in qs.iterator(chunk_size=200):
            goal = find_best_goal(txn)
            if goal is None:
                skipped += 1
                continue
            self.stdout.write(f'  [{txn.pk}] "{txn.label}" → "{goal.name}" (+{txn.amount}€)')
            if not dry_run:
                with db_transaction.atomic():
                    Transaction.objects.filter(pk=txn.pk).update(goal=goal)
                    goal.current_amount += txn.amount
                    goal.save(update_fields=['current_amount'])
            linked += 1

        suffix = ' [DRY RUN]' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\nLinked: {linked}, Skipped: {skipped}{suffix}'
        ))
