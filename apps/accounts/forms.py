"""Forms for registration, login and account settings."""
from __future__ import annotations

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.professionals.models import ProfessionalProfile

from .models import CustomerProfile, Gender, User


class CustomerRegistrationForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, strip=False
    )
    password2 = forms.CharField(
        label=_("Confirm password"), widget=forms.PasswordInput, strip=False
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "city"]

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean_password2(self) -> str:
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        password_validation.validate_password(p2, self.instance)
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()  # signal creates the CustomerProfile
        return user


class ProfessionalRegistrationForm(StyledFormMixin, forms.ModelForm):
    professional_type = forms.ChoiceField(
        label=_("I am registering as"),
        choices=ProfessionalProfile.ProfessionalType.choices,
        widget=forms.RadioSelect,
    )
    display_name = forms.CharField(
        label=_("Business / display name"), max_length=160
    )
    password1 = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, strip=False
    )
    password2 = forms.CharField(
        label=_("Confirm password"), widget=forms.PasswordInput, strip=False
    )

    field_order = [
        "professional_type",
        "display_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "password1",
        "password2",
    ]

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean_password2(self) -> str:
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        password_validation.validate_password(p2, self.instance)
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.role = User.Role.PROFESSIONAL
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(StyledFormMixin, AuthenticationForm):
    """Login by email; adds a *remember me* option."""

    remember_me = forms.BooleanField(label=_("Remember me"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Email")
        self.fields["username"].widget = forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email"}
        )
        # Re-apply styling after swapping the widget.
        self._style_fields()


class AccountSettingsForm(StyledFormMixin, forms.ModelForm):
    """Edit the account-level fields shown in dashboard settings."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "city",
            "date_of_birth",
            "gender",
            "avatar",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }


class CustomerProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ["date_of_birth", "gender", "city"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }
