from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='transaction',
            name='is_recurring',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transaction',
            name='recurrence',
            field=models.CharField(
                blank=True,
                choices=[('monthly', 'Mensuel'), ('weekly', 'Hebdomadaire'), ('yearly', 'Annuel')],
                default='',
                max_length=20,
            ),
        ),
    ]
