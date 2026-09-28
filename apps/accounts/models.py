"""Account-level models.

Only *account* information lives here. Anything specific to being a customer or a
professional belongs to the profile models (``CustomerProfile`` and the
``professionals`` app), keeping ``User`` small and role-agnostic.
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.uploads import avatar_upload_to
from apps.core.validators import validate_image_file

from .managers import UserManager


class Gender(models.TextChoices):
    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")
    UNDISCLOSED = "undisclosed", _("Prefer not to say")


class User(AbstractUser):
    """Custom user identified by a unique email address.

    ``role`` is the *account* role — never the professional type. A professional
    account's discipline (barber vs. salon) is stored on ``ProfessionalProfile``.
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        PROFESSIONAL = "professional", _("Professional")
        ADMIN = "admin", _("Admin")

    # ``username`` becomes optional/internal; email is the login identifier.
    username = models.CharField(
        _("username"),
        max_length=150,
        blank=True,
        null=True,
        help_text=_("Optional internal handle. Not used for login."),
    )
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(_("phone"), max_length=32, blank=True)
    avatar = models.ImageField(
        _("avatar"),
        upload_to=avatar_upload_to,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    role = models.CharField(
        _("account role"),
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )
    date_of_birth = models.DateField(_("date of birth"), blank=True, null=True)
    gender = models.CharField(
        _("gender"), max_length=20, choices=Gender.choices, blank=True
    )
    city = models.CharField(_("city"), max_length=120, blank=True)
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_("Set by staff only; drives the public verified badge."),
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # email + password are always prompted

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.email

    def get_full_name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.email.split("@")[0]

    @property
    def is_customer(self) -> bool:
        return self.role == self.Role.CUSTOMER

    @property
    def is_professional(self) -> bool:
        return self.role == self.Role.PROFESSIONAL

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    def get_absolute_url(self) -> str:
        return reverse("dashboard:index")


class CustomerProfile(models.Model):
    """Customer-specific profile data (one per customer account)."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="customer_profile"
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    city = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("customer profile")
        verbose_name_plural = _("customer profiles")

    def __str__(self) -> str:
        return f"Customer profile — {self.user}"
