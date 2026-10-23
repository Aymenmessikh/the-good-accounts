from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):
    """Collects the description, amount, and optional payer for an expense."""

    class Meta:
        model = Expense
        fields = ["description", "amount", "paid_by"]
        labels = {"description": "Description", "amount": "Montant (€)", "paid_by": "Payé par (facultatif)"}
