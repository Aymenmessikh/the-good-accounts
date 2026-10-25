from django.apps import AppConfig


class WalletsConfig(AppConfig):
    """Wallets app: shared wallets, members, invitations and settlement."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "wallets"
