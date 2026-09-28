"""In-app notifications.

Emails are handled separately in :mod:`apps.notifications.services`; this model
backs the navbar bell and the notifications page.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    BOOKING_CREATED = "booking_created", _("New appointment request")
    BOOKING_CONFIRMED = "booking_confirmed", _("Appointment confirmed")
    BOOKING_CANCELLED = "booking_cancelled", _("Appointment cancelled")
    BOOKING_COMPLETED = "booking_completed", _("Appointment completed")
    BOOKING_NO_SHOW = "booking_no_show", _("Marked as no-show")
    BOOKING_REMINDER = "booking_reminder", _("Appointment reminder")
    NEW_REVIEW = "new_review", _("New review")
    NEW_MESSAGE = "new_message", _("New message")


class NotificationQuerySet(models.QuerySet):
    def unread(self) -> "NotificationQuerySet":
        return self.filter(is_read=False)

    def for_user(self, user) -> "NotificationQuerySet":
        return self.filter(user=user)


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "created_at"])]

    def __str__(self) -> str:
        return f"{self.title} → {self.user}"
