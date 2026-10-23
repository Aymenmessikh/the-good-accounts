import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Wallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("is_closed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_wallets", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="wallets.wallet")),
            ],
        ),
        migrations.AddField(model_name="wallet", name="members", field=models.ManyToManyField(related_name="wallets", through="wallets.Membership", to=settings.AUTH_USER_MODEL)),
        migrations.AddConstraint(model_name="membership", constraint=models.UniqueConstraint(fields=("wallet", "user"), name="unique_wallet_member")),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("accepted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invited_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="wallets.wallet")),
            ],
        ),
        migrations.AddConstraint(model_name="invitation", constraint=models.UniqueConstraint(fields=("wallet", "email"), name="unique_wallet_invitation")),
    ]
