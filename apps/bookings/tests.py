"""Tests for the availability engine and booking rules — the critical path."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile, SalonMember
from apps.professionals.services import create_professional_profile
from apps.services.models import Service

from .models import Booking, BookingStatus
from .services import (
    BookingError,
    cancel_booking,
    complete_booking,
    confirm_booking,
    create_booking,
    get_available_slots,
    mark_no_show,
)


def next_weekday(base, weekday):
    """Return the next date on or after `base` that falls on `weekday` (0=Mon)."""
    days = (weekday - base.weekday()) % 7
    return base + dt.timedelta(days=days or 7)


class BookingTestBase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@example.com", password="pw", role=User.Role.CUSTOMER,
            first_name="Cara", phone="+994 50 111",
        )
        self.barber_user = User.objects.create_user(
            email="barber@example.com", password="pw", role=User.Role.PROFESSIONAL,
        )
        self.barber = create_professional_profile(
            user=self.barber_user,
            professional_type=ProfessionalProfile.ProfessionalType.BARBER,
            display_name="Test Barber",
        )
        self.service = Service.objects.create(
            professional=self.barber, name="Haircut", duration_minutes=30,
            price=Decimal("20"), show_price=True,
        )
        # A Wednesday (open 09:00–19:00 by default) safely in the future.
        self.date = next_weekday(timezone.localdate() + dt.timedelta(days=1), 2)


class AvailabilityTests(BookingTestBase):
    def test_slots_generated_within_working_hours(self):
        slots = get_available_slots(self.barber, self.service, self.date)
        self.assertTrue(slots)
        self.assertEqual(slots[0].start, dt.time(9, 0))
        # Last 30-min slot must end by 19:00.
        self.assertLessEqual(slots[-1].end, dt.time(19, 0))

    def test_no_slots_on_closed_day(self):
        sunday = next_weekday(self.date, 6)
        self.assertEqual(get_available_slots(self.barber, self.service, sunday), [])

    def test_no_slots_in_the_past(self):
        past = timezone.localdate() - dt.timedelta(days=1)
        self.assertEqual(get_available_slots(self.barber, self.service, past), [])

    def test_break_excludes_slots(self):
        self.barber.break_times.create(weekday=2, start_time=dt.time(13, 0), end_time=dt.time(14, 0))
        slots = get_available_slots(self.barber, self.service, self.date)
        starts = {s.start for s in slots}
        # A 30-min slot starting 13:00 or 13:30 would overlap the break.
        self.assertNotIn(dt.time(13, 0), starts)
        self.assertNotIn(dt.time(13, 30), starts)

    def test_day_off_removes_all_slots(self):
        self.barber.days_off.create(date=self.date, reason="Holiday")
        self.assertEqual(get_available_slots(self.barber, self.service, self.date), [])

    def test_existing_booking_removes_slot(self):
        create_booking(customer=self.customer, professional=self.barber, service=self.service,
                       date=self.date, start_time=dt.time(10, 0))
        starts = {s.start for s in get_available_slots(self.barber, self.service, self.date)}
        self.assertNotIn(dt.time(10, 0), starts)


class BookingCreationTests(BookingTestBase):
    def test_create_booking_sets_end_time_and_barber(self):
        booking = create_booking(customer=self.customer, professional=self.barber,
                                 service=self.service, date=self.date, start_time=dt.time(11, 0))
        self.assertEqual(booking.end_time, dt.time(11, 30))
        self.assertEqual(booking.status, BookingStatus.PENDING)
        self.assertEqual(booking.barber, self.barber.barber_profile)

    def test_double_booking_is_rejected(self):
        create_booking(customer=self.customer, professional=self.barber, service=self.service,
                       date=self.date, start_time=dt.time(10, 0))
        other = User.objects.create_user(email="c2@example.com", password="pw", role=User.Role.CUSTOMER)
        with self.assertRaises(BookingError):
            create_booking(customer=other, professional=self.barber, service=self.service,
                           date=self.date, start_time=dt.time(10, 0))

    def test_overlapping_booking_is_rejected(self):
        # 10:00–10:30 booked; a 10:15 start (10:15–10:45) overlaps.
        create_booking(customer=self.customer, professional=self.barber, service=self.service,
                       date=self.date, start_time=dt.time(10, 0))
        with self.assertRaises(BookingError):
            create_booking(customer=self.customer, professional=self.barber, service=self.service,
                           date=self.date, start_time=dt.time(10, 15))

    def test_cannot_book_in_past(self):
        past = timezone.localdate() - dt.timedelta(days=1)
        with self.assertRaises(BookingError):
            create_booking(customer=self.customer, professional=self.barber, service=self.service,
                           date=past, start_time=dt.time(10, 0))

    def test_cannot_book_outside_hours(self):
        with self.assertRaises(BookingError):
            create_booking(customer=self.customer, professional=self.barber, service=self.service,
                           date=self.date, start_time=dt.time(20, 0))

    def test_service_must_belong_to_professional(self):
        other_barber = create_professional_profile(
            user=User.objects.create_user(email="b2@example.com", password="pw", role=User.Role.PROFESSIONAL),
            professional_type=ProfessionalProfile.ProfessionalType.BARBER, display_name="Other",
        )
        foreign_service = Service.objects.create(professional=other_barber, name="X", duration_minutes=30)
        with self.assertRaises(BookingError):
            create_booking(customer=self.customer, professional=self.barber, service=foreign_service,
                           date=self.date, start_time=dt.time(12, 0))

    def test_cancelled_slot_becomes_available_again(self):
        booking = create_booking(customer=self.customer, professional=self.barber, service=self.service,
                                 date=self.date, start_time=dt.time(10, 0))
        cancel_booking(booking, by_customer=True)
        starts = {s.start for s in get_available_slots(self.barber, self.service, self.date)}
        self.assertIn(dt.time(10, 0), starts)


class StatusTransitionTests(BookingTestBase):
    def _booking(self):
        return create_booking(customer=self.customer, professional=self.barber,
                              service=self.service, date=self.date, start_time=dt.time(9, 0))

    def test_confirm_then_complete(self):
        b = self._booking()
        confirm_booking(b)
        self.assertEqual(b.status, BookingStatus.CONFIRMED)
        complete_booking(b)
        self.assertEqual(b.status, BookingStatus.COMPLETED)

    def test_cannot_complete_a_cancelled_booking(self):
        b = self._booking()
        cancel_booking(b, by_customer=False)
        with self.assertRaises(BookingError):
            complete_booking(b)

    def test_no_show_transition(self):
        b = self._booking()
        confirm_booking(b)
        mark_no_show(b)
        self.assertEqual(b.status, BookingStatus.NO_SHOW)


class SalonBookingTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="c@example.com", password="pw", role=User.Role.CUSTOMER)
        salon_user = User.objects.create_user(email="salon@example.com", password="pw", role=User.Role.PROFESSIONAL)
        self.salon = create_professional_profile(
            user=salon_user, professional_type=ProfessionalProfile.ProfessionalType.SALON, display_name="Salon",
        )
        self.salon_service = Service.objects.create(
            professional=self.salon, name="Cut", duration_minutes=30, price=Decimal("25"), show_price=True,
        )
        barber_user = User.objects.create_user(email="teamb@example.com", password="pw", role=User.Role.PROFESSIONAL)
        self.member_barber = create_professional_profile(
            user=barber_user, professional_type=ProfessionalProfile.ProfessionalType.BARBER, display_name="Member",
        )
        SalonMember.objects.create(salon=self.salon.salon_profile, barber=self.member_barber.barber_profile, is_active=True)
        self.date = next_weekday(timezone.localdate() + dt.timedelta(days=1), 2)

    def test_any_available_barber_gets_assigned(self):
        booking = create_booking(customer=self.customer, professional=self.salon,
                                 service=self.salon_service, date=self.date, start_time=dt.time(10, 0))
        self.assertEqual(booking.barber, self.member_barber.barber_profile)

    def test_specific_barber_requires_membership(self):
        outsider_user = User.objects.create_user(email="out@example.com", password="pw", role=User.Role.PROFESSIONAL)
        outsider = create_professional_profile(
            user=outsider_user, professional_type=ProfessionalProfile.ProfessionalType.BARBER, display_name="Outsider",
        )
        with self.assertRaises(BookingError):
            create_booking(customer=self.customer, professional=self.salon, service=self.salon_service,
                           date=self.date, start_time=dt.time(10, 0), barber=outsider.barber_profile)


class BookingApiPermissionTests(BookingTestBase):
    def test_customer_cannot_view_others_booking(self):
        booking = create_booking(customer=self.customer, professional=self.barber,
                                 service=self.service, date=self.date, start_time=dt.time(9, 0))
        intruder = User.objects.create_user(email="nosy@example.com", password="pw", role=User.Role.CUSTOMER)
        self.client.force_login(intruder)
        resp = self.client.get(f"/api/bookings/{booking.id}/")
        self.assertEqual(resp.status_code, 403)

    def test_create_booking_via_api(self):
        self.client.force_login(self.customer)
        resp = self.client.post("/api/bookings/", data={
            "professional": self.barber.id, "service": self.service.id,
            "date": self.date.isoformat(), "start_time": "14:00",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["success"])

    def test_double_booking_via_api_returns_error(self):
        self.client.force_login(self.customer)
        payload = {"professional": self.barber.id, "service": self.service.id,
                   "date": self.date.isoformat(), "start_time": "14:00"}
        first = self.client.post("/api/bookings/", data=payload, content_type="application/json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/bookings/", data=payload, content_type="application/json")
        self.assertEqual(second.status_code, 400)
        self.assertFalse(second.json()["success"])

    def test_notification_created_for_professional(self):
        with self.captureOnCommitCallbacks(execute=True):
            create_booking(customer=self.customer, professional=self.barber,
                           service=self.service, date=self.date, start_time=dt.time(9, 0))
        self.assertTrue(self.barber_user.notifications.filter(notification_type="booking_created").exists())
