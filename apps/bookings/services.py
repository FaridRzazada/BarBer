"""Availability engine + transactional booking creation & status transitions.

This module is the single source of truth for *when a professional can be booked*.
It never trusts the front-end: every rule (working hours, breaks, days off, past
times, existing bookings, service ownership, salon membership) is re-checked here
before a booking is written, inside a locked transaction that prevents two
customers from grabbing the same slot.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.professionals.models import (
    BarberProfile,
    ProfessionalProfile,
    SalonMember,
)

from .models import ACTIVE_STATUSES, Booking, BookingStatus


class BookingError(Exception):
    """Raised for any business-rule violation during booking."""


# ---------------------------------------------------------------------------
# Slot value object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Slot:
    start: dt.time
    end: dt.time
    available: bool = True

    @property
    def start_str(self) -> str:
        return self.start.strftime("%H:%M")

    @property
    def end_str(self) -> str:
        return self.end.strftime("%H:%M")

    def as_dict(self) -> dict:
        return {"start": self.start_str, "end": self.end_str, "available": self.available}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def _add_minutes(t: dt.time, minutes: int) -> dt.time:
    base = dt.datetime.combine(dt.date(2000, 1, 1), t)
    return (base + dt.timedelta(minutes=minutes)).time()


def _overlaps(s1: dt.time, e1: dt.time, s2: dt.time, e2: dt.time) -> bool:
    return s1 < e2 and s2 < e1


def _working_window(owner: ProfessionalProfile, date: dt.date) -> tuple[dt.time, dt.time] | None:
    """The open window for ``owner`` on ``date`` (None if closed / day off)."""
    for off in owner.days_off.all():
        if off.date == date:
            return None
    weekday = date.weekday()
    for wh in owner.working_hours.all():
        if wh.weekday == weekday and wh.is_open and wh.start_time and wh.end_time:
            return wh.start_time, wh.end_time
    return None


def _breaks_for(owner: ProfessionalProfile, date: dt.date) -> list[tuple[dt.time, dt.time]]:
    weekday = date.weekday()
    return [
        (b.start_time, b.end_time)
        for b in owner.break_times.all()
        if b.weekday == weekday
    ]


def _booked_intervals(block_q: Q, date: dt.date) -> list[tuple[dt.time, dt.time]]:
    qs = Booking.objects.filter(block_q, date=date, status__in=ACTIVE_STATUSES)
    return list(qs.values_list("start_time", "end_time"))


def _barber_block_q(barber: BarberProfile) -> Q:
    """Every booking that occupies this barber's time, in any context."""
    return Q(barber=barber) | Q(professional=barber.professional)


def _fits_schedule(
    start: dt.time,
    end: dt.time,
    window: tuple[dt.time, dt.time],
    breaks: list[tuple[dt.time, dt.time]],
) -> bool:
    win_start, win_end = window
    if start < win_start or end > win_end:
        return False
    for b_start, b_end in breaks:
        if _overlaps(start, end, b_start, b_end):
            return False
    return True


def _candidate_starts(window: tuple[dt.time, dt.time], duration: int) -> list[tuple[dt.time, dt.time]]:
    step = settings.BOOKING_SLOT_INTERVAL_MINUTES
    win_start, win_end = window
    cursor = win_start
    out: list[tuple[dt.time, dt.time]] = []
    # Guard against pathological configs.
    for _ in range(0, 24 * 60 // step + 1):
        end = _add_minutes(cursor, duration)
        if end > win_end:
            break
        out.append((cursor, end))
        cursor = _add_minutes(cursor, step)
        if cursor >= win_end:
            break
    return out


# ---------------------------------------------------------------------------
# Public: available slots
# ---------------------------------------------------------------------------
def _slots_for_resource(
    owner: ProfessionalProfile,
    block_q: Q,
    date: dt.date,
    duration: int,
    now: dt.datetime,
) -> list[Slot]:
    window = _working_window(owner, date)
    if window is None:
        return []
    breaks = _breaks_for(owner, date)
    booked = _booked_intervals(block_q, date)
    is_today = date == now.date()

    slots: list[Slot] = []
    for start, end in _candidate_starts(window, duration):
        if not _fits_schedule(start, end, window, breaks):
            continue
        if is_today and start <= now.time():
            continue
        if any(_overlaps(start, end, b_s, b_e) for b_s, b_e in booked):
            continue
        slots.append(Slot(start=start, end=end, available=True))
    return slots


def get_available_slots(
    professional: ProfessionalProfile,
    service,
    date: dt.date,
    barber: BarberProfile | None = None,
) -> list[Slot]:
    """Return the bookable slots for the given selection.

    * individual barber → the barber's own schedule
    * salon + specific barber → that barber's schedule (checked for membership)
    * salon + any available barber → salon window, kept if *some* active member is free
    """
    duration = service.duration_minutes
    now = timezone.localtime()

    if date < now.date() or date > now.date() + dt.timedelta(days=settings.BOOKING_MAX_ADVANCE_DAYS):
        return []

    # Concrete barber (individual, or salon + specific barber).
    concrete_barber = None
    if professional.is_barber:
        concrete_barber = getattr(professional, "barber_profile", None)
    elif barber is not None:
        concrete_barber = barber

    if concrete_barber is not None:
        owner = concrete_barber.professional
        return _slots_for_resource(owner, _barber_block_q(concrete_barber), date, duration, now)

    # Salon + any available barber.
    members = list(
        SalonMember.objects.filter(salon=professional.salon_profile, is_active=True)
        .select_related("barber__professional")
        .prefetch_related(
            "barber__professional__working_hours",
            "barber__professional__break_times",
            "barber__professional__days_off",
        )
    )
    if not members:
        # Salon with no team yet still bookable at the salon level.
        return _slots_for_resource(
            professional, Q(professional=professional), date, duration, now
        )

    # A salon slot is available if at least one member can take it.
    per_member_slots = [
        {
            (s.start, s.end)
            for s in _slots_for_resource(
                m.barber.professional, _barber_block_q(m.barber), date, duration, now
            )
        }
        for m in members
    ]
    union: set[tuple[dt.time, dt.time]] = set().union(*per_member_slots) if per_member_slots else set()
    return [Slot(start=s, end=e, available=True) for s, e in sorted(union)]


# ---------------------------------------------------------------------------
# Public: booking creation (transactional, race-safe)
# ---------------------------------------------------------------------------
def _validate_service(professional: ProfessionalProfile, service) -> None:
    if service.professional_id != professional.id:
        raise BookingError("This service does not belong to the selected professional.")
    if not service.is_active:
        raise BookingError("This service is not available for booking.")


def _pick_available_member(professional, service, date, start, end, now) -> BarberProfile | None:
    members = (
        SalonMember.objects.filter(salon=professional.salon_profile, is_active=True)
        .select_related("barber__professional")
        .prefetch_related(
            "barber__professional__working_hours",
            "barber__professional__break_times",
            "barber__professional__days_off",
        )
    )
    for m in members:
        owner = m.barber.professional
        window = _working_window(owner, date)
        if window is None:
            continue
        if not _fits_schedule(start, end, window, _breaks_for(owner, date)):
            continue
        booked = _booked_intervals(_barber_block_q(m.barber), date)
        if any(_overlaps(start, end, b_s, b_e) for b_s, b_e in booked):
            continue
        return m.barber
    return None


@transaction.atomic
def create_booking(
    *,
    customer,
    professional: ProfessionalProfile,
    service,
    date: dt.date,
    start_time: dt.time,
    barber: BarberProfile | None = None,
    notes: str = "",
) -> Booking:
    """Create a booking after re-validating availability under a row lock."""
    _validate_service(professional, service)

    now = timezone.localtime()
    if date < now.date():
        raise BookingError("You can't book a time in the past.")
    if date > now.date() + dt.timedelta(days=settings.BOOKING_MAX_ADVANCE_DAYS):
        raise BookingError("That date is too far in the future.")

    end_time = _add_minutes(start_time, service.duration_minutes)
    if end_time <= start_time:
        raise BookingError("Invalid time selection.")

    # Serialize concurrent bookings for the same professional resource.
    lock_pk = professional.pk
    if professional.is_salon and barber is not None:
        lock_pk = barber.professional_id
    ProfessionalProfile.objects.select_for_update().get(pk=lock_pk)

    # Resolve the concrete barber + schedule owner.
    if professional.is_barber:
        concrete_barber = getattr(professional, "barber_profile", None)
        owner = professional
    elif barber is not None:
        # Salon + specific barber: membership must be active.
        if not SalonMember.objects.filter(
            salon=professional.salon_profile, barber=barber, is_active=True
        ).exists():
            raise BookingError("That barber is not part of this salon's active team.")
        concrete_barber = barber
        owner = barber.professional
    else:
        # Salon + any available barber.
        concrete_barber = _pick_available_member(
            professional, service, date, start_time, end_time, now
        )
        if concrete_barber is not None:
            owner = concrete_barber.professional
        else:
            # No team members: book at the salon level.
            if SalonMember.objects.filter(
                salon=professional.salon_profile, is_active=True
            ).exists():
                raise BookingError("No barber is available at that time. Please pick another slot.")
            owner = professional

    # Re-check the slot against the resolved owner/barber.
    window = _working_window(owner, date)
    if window is None:
        raise BookingError("The professional is not open on that day.")
    if start_time.replace(microsecond=0) and date == now.date() and start_time <= now.time():
        raise BookingError("You can't book a time in the past.")
    if not _fits_schedule(start_time, end_time, window, _breaks_for(owner, date)):
        raise BookingError("That time is outside working hours or during a break.")

    block_q = _barber_block_q(concrete_barber) if concrete_barber else Q(professional=owner)
    if any(_overlaps(start_time, end_time, b_s, b_e) for b_s, b_e in _booked_intervals(block_q, date)):
        raise BookingError("This time slot is no longer available.")

    booking = Booking.objects.create(
        customer=customer,
        professional=professional,
        barber=concrete_barber,
        service=service,
        date=date,
        start_time=start_time,
        end_time=end_time,
        status=BookingStatus.PENDING,
        notes=notes,
    )

    # Notify the professional (in-app + email), outside the critical section.
    from apps.notifications.services import notify_booking_created

    transaction.on_commit(lambda: notify_booking_created(booking))
    return booking


# ---------------------------------------------------------------------------
# Public: status transitions
# ---------------------------------------------------------------------------
_ALLOWED_TRANSITIONS = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW, BookingStatus.COMPLETED},
    BookingStatus.CONFIRMED: {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW},
    BookingStatus.CANCELLED: set(),
    BookingStatus.COMPLETED: set(),
    BookingStatus.NO_SHOW: set(),
}


def _transition(booking: Booking, new_status: str) -> Booking:
    current = booking.status
    if new_status == current:
        return booking
    if new_status not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise BookingError(f"Cannot change a {current} booking to {new_status}.")
    booking.status = new_status
    booking.save(update_fields=["status", "updated_at"])
    return booking


def confirm_booking(booking: Booking) -> Booking:
    _transition(booking, BookingStatus.CONFIRMED)
    from apps.notifications.services import notify_booking_confirmed

    notify_booking_confirmed(booking)
    return booking


def complete_booking(booking: Booking) -> Booking:
    _transition(booking, BookingStatus.COMPLETED)
    from apps.notifications.services import notify_booking_completed

    notify_booking_completed(booking)
    return booking


def mark_no_show(booking: Booking) -> Booking:
    return _transition(booking, BookingStatus.NO_SHOW)


def cancel_booking(booking: Booking, *, by_customer: bool) -> Booking:
    if by_customer and not booking.can_customer_cancel:
        raise BookingError("This booking can no longer be cancelled.")
    _transition(booking, BookingStatus.CANCELLED)
    from apps.notifications.services import notify_booking_cancelled

    notify_booking_cancelled(booking, by_customer=by_customer)
    return booking
