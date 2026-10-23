from django import forms
from .models import Wallet


class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = ["name"]


class InvitationForm(forms.Form):
    email = forms.EmailField(label="Adresse e-mail")
