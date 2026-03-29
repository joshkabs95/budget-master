from django.db import migrations


class Migration(migrations.Migration):
    """
    wants_scores was already added by 0002_savingsrule_wants_scores via RunSQL IF NOT EXISTS.
    This migration is a no-op kept only for migration history continuity.
    """

    dependencies = [
        ('savings', '0003_merge'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE savings_rules ADD COLUMN IF NOT EXISTS wants_scores jsonb NOT NULL DEFAULT '{}'::jsonb;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
