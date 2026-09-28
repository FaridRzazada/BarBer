"""Expose unread notification count + a small recent list to every template."""
from __future__ import annotations

from .models import Notification


def notifications(request) -> dict:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"unread_notifications_count": 0, "recent_notifications": []}

    qs = Notification.objects.for_user(user)
    unread = qs.unread().count()
    recent = list(qs[:6])
    return {
        "unread_notifications_count": unread,
        "recent_notifications": recent,
    }
