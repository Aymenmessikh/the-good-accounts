from django import forms
from .models import Wallet


class WalletForm(forms.ModelForm):
    """Collects the information needed to create a wallet."""

    class Meta:
        model = Wallet
        fields = ["name"]


class InvitationForm(forms.Form):
    """Collects the email address of the person to invite."""

    email = forms.EmailField(label="Adresse e-mail")
