from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_notes_recurring'),
        ('goals', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='goal',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transactions',
                to='goals.goal',
            ),
        ),
    ]
