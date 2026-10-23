import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("wallets", "0001_initial"), ("accounts", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_expenses", to=settings.AUTH_USER_MODEL)),
                ("paid_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paid_expenses", to=settings.AUTH_USER_MODEL)),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="wallets.wallet")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
