"""Services offered by professionals.

``ServiceCategory`` is a shared taxonomy (Haircut, Beard, Colouring …). Each
``Service`` belongs to a single professional — services are never global rows
duplicated per professional.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.utils import unique_slugify


class ServiceCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("service category")
        verbose_name_plural = _("service categories")
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class ServiceQuerySet(models.QuerySet):
    def active(self) -> "ServiceQuerySet":
        return self.filter(is_active=True)

    def for_professional(self, professional) -> "ServiceQuerySet":
        return self.filter(professional=professional)


class Service(models.Model):
    professional = models.ForeignKey(
        "professionals.ProfessionalProfile",
        on_delete=models.CASCADE,
        related_name="services",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        help_text=_("Duration in minutes — required; drives the booking engine.")
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    show_price = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ["category__order", "name"]
        indexes = [
            models.Index(fields=["professional", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.duration_minutes} min)"

    @property
    def price_display(self) -> str | None:
        if self.show_price and self.price is not None:
            return f"{self.price:g}"
        return None
