from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin


class ReviewForm(StyledFormMixin, forms.Form):
    rating = forms.TypedChoiceField(
        label=_("Rating"),
        choices=[(i, f"{i} ★") for i in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
    )
    comment = forms.CharField(
        label=_("Your review"),
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )
