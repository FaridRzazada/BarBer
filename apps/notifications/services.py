"""Notification dispatch — a single place for in-app + email notifications.

Views never build emails or notifications inline; they call these functions so
the behaviour is consistent, testable and easy to extend (SMS, push, …) later.
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from .models import Notification, NotificationType


def absolute_url(path: str) -> str:
    return f"{settings.SITE_URL.rstrip('/')}{path}"


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def create_notification(*, user, notification_type: str, title: str, message: str = "", url: str = "") -> Notification:
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        url=url,
    )


def send_email(*, subject: str, recipient: str, template: str, context: dict) -> None:
    """Render ``notifications/emails/<template>.{txt,html}`` and send it."""
    if not recipient:
        return
    ctx = {"SITE_NAME": settings.SITE_NAME, **context}
    text_body = render_to_string(f"notifications/emails/{template}.txt", ctx)
    try:
        html_body = render_to_string(f"notifications/emails/{template}.html", ctx)
    except Exception:  # pragma: no cover - HTML template optional
        html_body = None

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body or strip_tags(html_body or ""),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    if html_body:
        email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=True)


def _booking_context(booking) -> dict:
    return {
        "booking": booking,
        "customer": booking.customer,
        "professional": booking.professional,
        "service": booking.service,
        "dashboard_url": absolute_url(reverse("dashboard:index")),
        "booking_url": absolute_url(booking.get_absolute_url()),
    }


# ---------------------------------------------------------------------------
# High-level booking notifications
# ---------------------------------------------------------------------------
def notify_booking_created(booking) -> None:
    """A customer requested an appointment → tell the professional."""
    professional_user = booking.professional.user
    create_notification(
        user=professional_user,
        notification_type=NotificationType.BOOKING_CREATED,
        title="New appointment request",
        message=f"{booking.customer.display_name} requested {booking.service.name} on {booking.date} at {booking.start_time:%H:%M}.",
        url=booking.get_absolute_url(),
    )
    send_email(
        subject=f"New appointment request — {booking.service.name}",
        recipient=professional_user.email,
        template="booking_created",
        context=_booking_context(booking),
    )


def notify_booking_confirmed(booking) -> None:
    create_notification(
        user=booking.customer,
        notification_type=NotificationType.BOOKING_CONFIRMED,
        title="Appointment confirmed",
        message=f"{booking.professional.display_name} confirmed your {booking.service.name} on {booking.date} at {booking.start_time:%H:%M}.",
        url=booking.get_absolute_url(),
    )
    send_email(
        subject="Your appointment is confirmed",
        recipient=booking.customer.email,
        template="booking_confirmed",
        context=_booking_context(booking),
    )


def notify_booking_cancelled(booking, *, by_customer: bool) -> None:
    if by_customer:
        # Tell the professional their slot freed up.
        recipient_user = booking.professional.user
        title = "Appointment cancelled"
        message = f"{booking.customer.display_name} cancelled the {booking.service.name} on {booking.date}."
    else:
        recipient_user = booking.customer
        title = "Appointment cancelled"
        message = f"{booking.professional.display_name} cancelled your {booking.service.name} on {booking.date}."
    create_notification(
        user=recipient_user,
        notification_type=NotificationType.BOOKING_CANCELLED,
        title=title,
        message=message,
        url=booking.get_absolute_url(),
    )
    send_email(
        subject="Appointment cancelled",
        recipient=recipient_user.email,
        template="booking_cancelled",
        context={**_booking_context(booking), "by_customer": by_customer},
    )


def notify_booking_completed(booking) -> None:
    create_notification(
        user=booking.customer,
        notification_type=NotificationType.BOOKING_COMPLETED,
        title="How was your visit?",
        message=f"Your {booking.service.name} with {booking.professional.display_name} is complete. Leave a review!",
        url=booking.get_absolute_url(),
    )


def notify_new_review(review) -> None:
    create_notification(
        user=review.professional.user,
        notification_type=NotificationType.NEW_REVIEW,
        title="New review",
        message=f"{review.customer.display_name} left you a {review.rating}★ review.",
        url=review.professional.get_absolute_url(),
    )


def notify_new_message(message) -> None:
    """Notify the message recipient (the party who is *not* the sender)."""
    conversation = message.conversation
    professional_user = conversation.professional.user
    if message.sender_id == conversation.customer_id:
        recipient = professional_user
    else:
        recipient = conversation.customer
    create_notification(
        user=recipient,
        notification_type=NotificationType.NEW_MESSAGE,
        title="New message",
        message=f"{message.sender.display_name}: {message.body[:60]}",
        url=reverse("messaging:index"),
    )
