"""Professional domain models.

Relationship overview::

    User ─1:1─ ProfessionalProfile ─1:1─ BarberProfile
                                    └1:1─ SalonProfile ─┐
    SalonProfile ─* SalonMember *─ BarberProfile        │
    ProfessionalProfile ─* WorkingHour / BreakTime / DayOff
                        ─* PortfolioImage / ProfessionalGallery
                        ─* Favorite (via User)

A barber always has their own account; a salon merely *references* existing
barbers through ``SalonMember`` — it never owns a second user.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count, Min, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.uploads import (
    gallery_upload_to,
    portfolio_upload_to,
    professional_cover_upload_to,
    professional_profile_image_upload_to,
)
from apps.core.utils import unique_slugify
from apps.core.validators import validate_image_file


class Weekday(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class ProfessionalQuerySet(models.QuerySet):
    def active(self) -> "ProfessionalQuerySet":
        return self.filter(is_active=True)

    def verified(self) -> "ProfessionalQuerySet":
        return self.filter(is_verified=True)

    def of_type(self, professional_type: str | None) -> "ProfessionalQuerySet":
        if professional_type in (ProfessionalProfile.ProfessionalType.values):
            return self.filter(professional_type=professional_type)
        return self

    def locatable(self) -> "ProfessionalQuerySet":
        return self.filter(latitude__isnull=False, longitude__isnull=False)

    def with_rating(self) -> "ProfessionalQuerySet":
        return self.annotate(
            rating_avg=Avg("reviews__rating"),
            rating_count=Count("reviews", distinct=True),
        )

    def with_min_price(self) -> "ProfessionalQuerySet":
        return self.annotate(
            min_price=Min(
                "services__price",
                filter=Q(
                    services__is_active=True,
                    services__show_price=True,
                    services__price__isnull=False,
                ),
            )
        )

    def for_cards(self) -> "ProfessionalQuerySet":
        """Everything a professional card needs, without N+1 queries."""
        return (
            self.select_related("user", "barber_profile", "salon_profile")
            .with_rating()
            .with_min_price()
        )


class ProfessionalProfile(models.Model):
    class ProfessionalType(models.TextChoices):
        BARBER = "barber", _("Barber")
        SALON = "salon", _("Salon")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_profile",
    )
    professional_type = models.CharField(
        max_length=20, choices=ProfessionalType.choices, db_index=True
    )
    display_name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)

    phone = models.CharField(max_length=32, blank=True)
    public_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    profile_image = models.ImageField(
        upload_to=professional_profile_image_upload_to,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    cover_image = models.ImageField(
        upload_to=professional_cover_upload_to,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )

    is_verified = models.BooleanField(
        default=False, help_text=_("Set by staff only — powers the verified badge.")
    )
    is_active = models.BooleanField(
        default=True, help_text=_("Inactive profiles are hidden from public search.")
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProfessionalQuerySet.as_manager()

    class Meta:
        verbose_name = _("professional")
        verbose_name_plural = _("professionals")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["professional_type"]),
            models.Index(fields=["city"]),
            models.Index(fields=["is_active", "is_verified"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.display_name
            if self.city:
                base = f"{self.display_name} {self.city}"
            self.slug = unique_slugify(self, base)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("professionals:detail", kwargs={"slug": self.slug})

    # -- convenience -------------------------------------------------------
    @property
    def is_barber(self) -> bool:
        return self.professional_type == self.ProfessionalType.BARBER

    @property
    def is_salon(self) -> bool:
        return self.professional_type == self.ProfessionalType.SALON

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def type_label(self) -> str:
        return self.get_professional_type_display()

    @property
    def starting_price(self) -> Decimal | None:
        """Lowest visible price, if the professional chose to publish one."""
        # Prefer an annotated value (list views) to avoid extra queries.
        annotated = getattr(self, "min_price", "unset")
        if annotated != "unset":
            if annotated is not None:
                return annotated
        else:
            price = (
                self.services.filter(
                    is_active=True, show_price=True, price__isnull=False
                )
                .order_by("price")
                .values_list("price", flat=True)
                .first()
            )
            if price is not None:
                return price
        # Fall back to the sub-profile's declared price range.
        sub = self.barber_profile if self.is_barber else getattr(self, "salon_profile", None)
        if sub and sub.show_price and sub.price_from is not None:
            return sub.price_from
        return None


class BarberProfile(models.Model):
    professional = models.OneToOneField(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="barber_profile"
    )
    bio = models.TextField(blank=True)
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    show_price = models.BooleanField(default=False)
    price_from = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    price_to = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = _("barber profile")
        verbose_name_plural = _("barber profiles")

    def __str__(self) -> str:
        return f"Barber — {self.professional.display_name}"


class SalonProfile(models.Model):
    professional = models.OneToOneField(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="salon_profile"
    )
    description = models.TextField(blank=True)
    number_of_workers = models.PositiveSmallIntegerField(null=True, blank=True)
    show_price = models.BooleanField(default=False)
    price_from = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    price_to = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = _("salon profile")
        verbose_name_plural = _("salon profiles")

    def __str__(self) -> str:
        return f"Salon — {self.professional.display_name}"


class SalonMember(models.Model):
    """Links an independent barber to a salon's team (no second user created)."""

    salon = models.ForeignKey(
        SalonProfile, on_delete=models.CASCADE, related_name="members"
    )
    barber = models.ForeignKey(
        BarberProfile, on_delete=models.CASCADE, related_name="salon_memberships"
    )
    position = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("salon team member")
        verbose_name_plural = _("salon team members")
        constraints = [
            models.UniqueConstraint(
                fields=["salon", "barber"], name="unique_salon_barber"
            )
        ]
        ordering = ["position", "joined_at"]

    def __str__(self) -> str:
        return f"{self.barber.professional.display_name} @ {self.salon.professional.display_name}"


class WorkingHour(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    is_open = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("working hour")
        verbose_name_plural = _("working hours")
        ordering = ["weekday"]
        constraints = [
            models.UniqueConstraint(
                fields=["professional", "weekday"], name="unique_professional_weekday"
            )
        ]

    def __str__(self) -> str:
        if not self.is_open:
            return f"{self.get_weekday_display()}: Closed"
        return f"{self.get_weekday_display()}: {self.start_time}–{self.end_time}"


class BreakTime(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="break_times"
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name = _("break time")
        verbose_name_plural = _("break times")
        ordering = ["weekday", "start_time"]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} break {self.start_time}–{self.end_time}"


class DayOff(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="days_off"
    )
    date = models.DateField()
    reason = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name = _("day off")
        verbose_name_plural = _("days off")
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["professional", "date"], name="unique_professional_dayoff"
            )
        ]

    def __str__(self) -> str:
        return f"{self.professional.display_name} off on {self.date}"


class PortfolioImage(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="portfolio_images"
    )
    image = models.ImageField(
        upload_to=portfolio_upload_to, validators=[validate_image_file]
    )
    title = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = _("portfolio image")
        verbose_name_plural = _("portfolio images")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or f"Portfolio #{self.pk}"


class ProfessionalGallery(models.Model):
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.ImageField(
        upload_to=gallery_upload_to, validators=[validate_image_file]
    )
    title = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = _("gallery image")
        verbose_name_plural = _("gallery images")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or f"Gallery #{self.pk}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = _("favorite")
        verbose_name_plural = _("favorites")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "professional"], name="unique_user_favorite"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.professional}"
