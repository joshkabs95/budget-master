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
            name='BankAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('bank_name', models.CharField(blank=True, default='', max_length=100)),
                ('account_type', models.CharField(
                    choices=[
                        ('checking', 'Compte courant'),
                        ('joint', 'Compte joint'),
                        ('pro', 'Compte professionnel'),
                        ('other', 'Autre'),
                    ],
                    default='checking',
                    max_length=20,
                )),
                ('initial_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('color', models.CharField(default='#00D4AA', max_length=7)),
                ('icon', models.CharField(default='🏦', max_length=10)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bank_accounts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'bank_accounts', 'ordering': ['-created_at']},
        ),
    ]
