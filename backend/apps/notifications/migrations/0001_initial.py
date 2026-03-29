from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[
                    ('risk_high', 'Risque élevé'), ('budget_exceeded', 'Budget dépassé'),
                    ('budget_warning', 'Budget en alerte'), ('anomaly', 'Anomalie détectée'),
                    ('savings_gap', 'Écart épargne'), ('risk_score', 'Score de risque'),
                    ('streak', 'Streak épargne'), ('info', 'Information'),
                ], max_length=30)),
                ('severity', models.CharField(choices=[('green', 'green'), ('orange', 'orange'), ('red', 'red')], default='orange', max_length=10)),
                ('message', models.TextField()),
                ('read', models.BooleanField(default=False)),
                ('email_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'notifications', 'ordering': ['-created_at']},
        ),
    ]
