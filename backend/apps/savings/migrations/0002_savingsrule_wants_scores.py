from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('savings', '0001_initial')]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE savings_rules ADD COLUMN IF NOT EXISTS wants_scores jsonb NOT NULL DEFAULT '{}'",
            reverse_sql="ALTER TABLE savings_rules DROP COLUMN IF EXISTS wants_scores",
        )
    ]
