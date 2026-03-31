from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('savings', '0004_savingsrule_wants_scores'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='savingsaccount',
            options={'ordering': ['-initial_balance']},
        ),
        migrations.RenameField(
            model_name='savingsaccount',
            old_name='balance',
            new_name='initial_balance',
        ),
    ]
