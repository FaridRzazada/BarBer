"""Dashboard forms for professionals (profile, services, media, products, team)."""
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.professionals.models import (
    BarberProfile,
    BreakTime,
    DayOff,
    ProfessionalGallery,
    ProfessionalProfile,
    PortfolioImage,
    SalonProfile,
    Weekday,
)
from apps.products.models import Product
from apps.services.models import Service


class ProfessionalProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProfessionalProfile
        fields = [
            "display_name",
            "description",
            "phone",
            "public_email",
            "website",
            "address",
            "city",
            "latitude",
            "longitude",
            "profile_image",
            "cover_image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "latitude": forms.NumberInput(attrs={"step": "any", "readonly": "readonly"}),
            "longitude": forms.NumberInput(attrs={"step": "any", "readonly": "readonly"}),
        }


class BarberProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BarberProfile
        fields = ["bio", "experience_years", "specialization", "show_price", "price_from", "price_to"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class SalonProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SalonProfile
        fields = ["description", "number_of_workers", "show_price", "price_from", "price_to"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ServiceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["category", "name", "description", "duration_minutes", "price", "show_price", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def clean_duration_minutes(self):
        value = self.cleaned_data["duration_minutes"]
        if value <= 0:
            raise forms.ValidationError(_("Duration must be greater than zero."))
        return value


class PortfolioImageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PortfolioImage
        fields = ["image", "title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class GalleryImageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProfessionalGallery
        fields = ["image", "title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "description",
            "brand",
            "price",
            "currency",
            "stock",
            "is_available",
            "main_image",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class BreakTimeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BreakTime
        fields = ["weekday", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and start >= end:
            raise forms.ValidationError(_("Break end must be after its start."))
        return cleaned


class DayOffForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DayOff
        fields = ["date", "reason"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class SalonMemberForm(StyledFormMixin, forms.Form):
    """Add an *existing* barber (by account email) to the salon team."""

    barber_email = forms.EmailField(label=_("Barber's account email"))
    position = forms.CharField(label=_("Position"), max_length=120, required=False)

    def clean_barber_email(self):
        email = self.cleaned_data["barber_email"].strip().lower()
        try:
            barber = BarberProfile.objects.select_related("professional__user").get(
                professional__user__email__iexact=email
            )
        except BarberProfile.DoesNotExist:
            raise forms.ValidationError(
                _("No barber account was found with that email. They must register as a barber first.")
            )
        self.barber = barber
        return email
