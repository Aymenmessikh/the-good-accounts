from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Accounts app: users, sign-up, login, profile and auth API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"