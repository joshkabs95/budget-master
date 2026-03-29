from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.CharField(max_length=7)),
                ('allocated', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('carried_over', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to='categories.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='category_budgets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'category_budgets',
                'ordering': ['category__name'],
                'unique_together': {('user', 'category', 'month')},
            },
        ),
    ]
