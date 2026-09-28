"""Shared form helpers.

``StyledFormMixin`` applies consistent CSS classes to every widget so all forms
across the project share one look without repeating widget attrs everywhere.
"""
from __future__ import annotations

from django import forms

from .models import ContactMessage, Report


class StyledFormMixin:
    """Attach design-system CSS classes to a form's widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def _style_fields(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form__check-input")
            elif isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                widget.attrs.setdefault("class", "form__choice")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form__control")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "form__control")
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("class", "form__file")
            else:
                widget.attrs.setdefault("class", "form__control")
                # A gentle placeholder derived from the label improves UX.
                if field.label and "placeholder" not in widget.attrs:
                    widget.attrs["placeholder"] = str(field.label)


class ContactForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]


class ReportForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "description"]
