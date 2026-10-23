from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["description", "amount", "paid_by"]
        labels = {"description": "Description", "amount": "Montant (€)", "paid_by": "Payé par (facultatif)"}
