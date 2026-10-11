from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", strip=False, widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirm password", strip=False, widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                candidate = User(
                    email=cleaned.get("email", ""),
                    first_name=cleaned.get("first_name", ""),
                    last_name=cleaned.get("last_name", ""),
                )
                try:
                    validate_password(password1, user=candidate)
                except ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    """Login form using the email (Django's form always names the field 'username')."""

    username = forms.EmailField(
        label="Email", widget=forms.EmailInput(attrs={"autofocus": True})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_username(self):
        # Emails are stored in lowercase, so "Alice@X.com" must still work
        return self.cleaned_data["username"].lower()