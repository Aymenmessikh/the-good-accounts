from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    """Expenses app: expenses recorded in a wallet."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "expenses"
