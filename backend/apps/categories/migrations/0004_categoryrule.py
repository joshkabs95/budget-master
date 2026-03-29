from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_categorybudget'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyword', models.CharField(max_length=100)),
                ('priority', models.PositiveSmallIntegerField(default=0, help_text='Plus élevé = prioritaire')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='categories.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='category_rules', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'category_rules',
                'ordering': ['-priority', 'keyword'],
                'unique_together': {('user', 'keyword')},
            },
        ),
    ]
