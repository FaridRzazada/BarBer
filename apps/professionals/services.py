"""Business logic for professionals.

Kept out of views so it can be reused (registration, onboarding, API) and unit
tested in isolation.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .models import (
    BarberProfile,
    ProfessionalProfile,
    SalonProfile,
    WorkingHour,
)

# Sensible starting schedule applied at registration; fully editable later.
_DEFAULT_HOURS = {
    0: (dt.time(9, 0), dt.time(19, 0)),
    1: (dt.time(9, 0), dt.time(19, 0)),
    2: (dt.time(9, 0), dt.time(19, 0)),
    3: (dt.time(9, 0), dt.time(19, 0)),
    4: (dt.time(9, 0), dt.time(20, 0)),
    5: (dt.time(10, 0), dt.time(18, 0)),
    6: None,  # Sunday closed
}


@transaction.atomic
def create_professional_profile(
    *, user, professional_type: str, display_name: str
) -> ProfessionalProfile:
    """Create the professional profile, its typed sub-profile and default hours."""
    profile = ProfessionalProfile.objects.create(
        user=user,
        professional_type=professional_type,
        display_name=display_name,
        city=user.city or "",
    )
    if profile.is_barber:
        BarberProfile.objects.create(professional=profile)
    else:
        SalonProfile.objects.create(professional=profile)

    working_hours = []
    for weekday, span in _DEFAULT_HOURS.items():
        if span is None:
            working_hours.append(
                WorkingHour(professional=profile, weekday=weekday, is_open=False)
            )
        else:
            start, end = span
            working_hours.append(
                WorkingHour(
                    professional=profile,
                    weekday=weekday,
                    is_open=True,
                    start_time=start,
                    end_time=end,
                )
            )
    WorkingHour.objects.bulk_create(working_hours)
    return profile


def is_open_now(professional: ProfessionalProfile, at: dt.datetime | None = None) -> bool:
    """Whether the professional is currently open.

    Uses ``.all()`` on related sets so a caller that prefetches
    ``working_hours``/``break_times``/``days_off`` incurs no extra queries.
    """
    at = timezone.localtime(at) if at else timezone.localtime()
    today = at.date()
    weekday = today.weekday()
    now_time = at.time()

    for off in professional.days_off.all():
        if off.date == today:
            return False

    open_hour = None
    for wh in professional.working_hours.all():
        if wh.weekday == weekday and wh.is_open and wh.start_time and wh.end_time:
            open_hour = wh
            break
    if open_hour is None:
        return False
    if not (open_hour.start_time <= now_time <= open_hour.end_time):
        return False

    for br in professional.break_times.all():
        if br.weekday == weekday and br.start_time <= now_time < br.end_time:
            return False
    return True


@dataclass
class CompletionSection:
    key: str
    label: str
    done: bool


def compute_profile_completion(professional: ProfessionalProfile) -> dict:
    """Return completion percentage + per-section status (never hard-coded)."""
    has_working_hours = any(
        wh.is_open and wh.start_time and wh.end_time
        for wh in professional.working_hours.all()
    )
    sections = [
        CompletionSection("basic", "Basic information", bool(professional.description.strip())),
        CompletionSection("location", "Location", professional.has_location),
        CompletionSection("hours", "Working hours", has_working_hours),
        CompletionSection("services", "Services", professional.services.filter(is_active=True).exists()),
        CompletionSection("profile_image", "Profile image", bool(professional.profile_image)),
        CompletionSection("cover_image", "Cover image", bool(professional.cover_image)),
        CompletionSection("portfolio", "Portfolio", professional.portfolio_images.exists()),
        CompletionSection("gallery", "Gallery", professional.gallery_images.exists()),
        CompletionSection(
            "contact",
            "Contact information",
            bool(professional.phone or professional.public_email),
        ),
    ]
    done = sum(1 for s in sections if s.done)
    percent = round(done / len(sections) * 100)
    return {
        "percent": percent,
        "done": done,
        "total": len(sections),
        "sections": sections,
        "is_complete": done == len(sections),
    }
