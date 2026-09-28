"""Booking model + status enum.

A booking always references a *professional* (barber account or salon) and a
*service*. ``barber`` is nullable and only set for salon bookings that target a
specific team member (or that the engine assigns for "any available barber").
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BookingStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    CANCELLED = "cancelled", _("Cancelled")
    COMPLETED = "completed", _("Completed")
    NO_SHOW = "no_show", _("No-show")


# Which statuses still occupy a time slot (block other bookings).
ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


class BookingQuerySet(models.QuerySet):
    def active(self) -> "BookingQuerySet":
        """Bookings that still hold their slot."""
        return self.filter(status__in=ACTIVE_STATUSES)

    def upcoming(self) -> "BookingQuerySet":
        return self.filter(date__gte=timezone.localdate())

    def for_customer(self, user) -> "BookingQuerySet":
        return self.filter(customer=user)

    def for_professional(self, professional) -> "BookingQuerySet":
        return self.filter(professional=professional)


class Booking(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    professional = models.ForeignKey(
        "professionals.ProfessionalProfile",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    barber = models.ForeignKey(
        "professionals.BarberProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barber_bookings",
    )
    service = models.ForeignKey(
        "services.Service", on_delete=models.PROTECT, related_name="bookings"
    )

    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        verbose_name = _("booking")
        verbose_name_plural = _("bookings")
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["professional", "date", "status"]),
            models.Index(fields=["barber", "date", "status"]),
            models.Index(fields=["customer", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.customer} · {self.service} · {self.date} {self.start_time}"

    # -- status helpers ----------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_past(self) -> bool:
        now = timezone.localtime()
        if self.date < now.date():
            return True
        return self.date == now.date() and self.end_time <= now.time()

    @property
    def can_customer_cancel(self) -> bool:
        return self.status in (BookingStatus.PENDING, BookingStatus.CONFIRMED) and not self.is_past

    @property
    def can_be_reviewed(self) -> bool:
        return self.status == BookingStatus.COMPLETED and not hasattr(self, "review")

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("bookings:detail", kwargs={"pk": self.pk})
