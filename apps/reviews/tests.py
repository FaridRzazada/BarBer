import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingStatus
from apps.professionals.models import ProfessionalProfile
from apps.professionals.services import create_professional_profile
from apps.services.models import Service

from .models import Review
from .services import ReviewError, create_review, rating_summary


class ReviewTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="c@example.com", password="pw", role=User.Role.CUSTOMER)
        self.pro = create_professional_profile(
            user=User.objects.create_user(email="p@example.com", password="pw", role=User.Role.PROFESSIONAL),
            professional_type=ProfessionalProfile.ProfessionalType.BARBER, display_name="Barber",
        )
        self.service = Service.objects.create(professional=self.pro, name="Cut", duration_minutes=30)

    def _booking(self, status):
        return Booking.objects.create(
            customer=self.customer, professional=self.pro, service=self.service,
            date=timezone.localdate() - dt.timedelta(days=1),
            start_time=dt.time(10, 0), end_time=dt.time(10, 30), status=status,
        )

    def test_review_requires_completed_booking(self):
        booking = self._booking(BookingStatus.CONFIRMED)
        with self.assertRaises(ReviewError):
            create_review(customer=self.customer, booking=booking, rating=5)

    def test_review_on_completed_booking(self):
        booking = self._booking(BookingStatus.COMPLETED)
        review = create_review(customer=self.customer, booking=booking, rating=5, comment="Great")
        self.assertEqual(review.professional, self.pro)

    def test_cannot_review_twice(self):
        booking = self._booking(BookingStatus.COMPLETED)
        create_review(customer=self.customer, booking=booking, rating=4)
        with self.assertRaises(ReviewError):
            create_review(customer=self.customer, booking=booking, rating=3)

    def test_only_own_booking(self):
        other = User.objects.create_user(email="o@example.com", password="pw", role=User.Role.CUSTOMER)
        booking = self._booking(BookingStatus.COMPLETED)
        with self.assertRaises(ReviewError):
            create_review(customer=other, booking=booking, rating=5)

    def test_rating_summary(self):
        b1 = self._booking(BookingStatus.COMPLETED)
        create_review(customer=self.customer, booking=b1, rating=5)
        summary = rating_summary(self.pro)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["average"], 5.0)
        self.assertEqual(summary["distribution"][5], 1)
