from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('transactions', '0004_transaction_goal'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReconciliationSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('month', models.CharField(max_length=7)),
                ('status', models.CharField(choices=[('open', 'Ouverte'), ('closed', 'Clôturée')], default='open', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reconciliation_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'reconciliation_sessions', 'ordering': ['-month'], 'unique_together': {('user', 'month')}},
        ),
        migrations.CreateModel(
            name='ReconciliationEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('bank_date', models.DateField(blank=True, null=True)),
                ('bank_label', models.CharField(blank=True, max_length=255)),
                ('bank_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[('auto', 'Auto'), ('manual', 'Manuel'), ('unmatched_app', 'Non trouvé en banque'), ('unmatched_bank', 'Non trouvé dans l\'app')], default='unmatched_bank', max_length=20)),
                ('match_score', models.FloatField(default=0)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='reconciliation.reconciliationsession')),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reconciliation_entries', to='transactions.transaction')),
            ],
            options={'db_table': 'reconciliation_entries', 'ordering': ['bank_date', 'bank_amount']},
        ),
    ]
