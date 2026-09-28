"""Signals that keep profile rows in sync with account role."""
from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile, User


@receiver(post_save, sender=User)
def ensure_customer_profile(sender, instance: User, created: bool, **kwargs) -> None:
    """Every customer account gets a ``CustomerProfile``.

    Professional profiles are created explicitly during professional
    registration / onboarding, so they are intentionally not handled here.
    """
    if instance.role == User.Role.CUSTOMER:
        CustomerProfile.objects.get_or_create(user=instance)
