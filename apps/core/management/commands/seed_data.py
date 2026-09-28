"""Seed development/demo data.

Creates clearly-labelled DEMO accounts, professionals, services, bookings and
reviews so the app can be explored end-to-end. Never run this against a real
production database — every account here uses a known password.

    python manage.py seed_data
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
from apps.locations.models import City
from apps.products.models import Product, ProductCategory
from apps.professionals.models import ProfessionalProfile, SalonMember
from apps.professionals.services import create_professional_profile
from apps.reviews.models import Review
from apps.services.models import Service, ServiceCategory
from apps.accounts.models import User

DEMO_PASSWORD = "demo12345"
BAKU = (40.4093, 49.8671)

SERVICE_CATEGORIES = [
    "Haircut", "Fade", "Beard", "Hair + Beard", "Shaving",
    "Hair Coloring", "Styling", "Kids Haircut", "Facial",
]
PRODUCT_CATEGORIES = ["Hair care", "Beard care", "Styling", "Tools"]
CITIES = [
    ("Baku", 40.4093, 49.8671),
    ("Ganja", 40.6828, 46.3606),
    ("Sumqayit", 40.5897, 49.6686),
]


class Command(BaseCommand):
    help = "Seed the database with demo data for development."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self.stdout.write("Seeding reference data…")
        cats = {name: ServiceCategory.objects.get_or_create(name=name)[0] for name in SERVICE_CATEGORIES}
        for i, name in enumerate(PRODUCT_CATEGORIES):
            ProductCategory.objects.get_or_create(name=name, defaults={"order": i})
        for name, lat, lng in CITIES:
            City.objects.get_or_create(name=name, defaults={"latitude": lat, "longitude": lng})

        customer = self._customer()
        barbers = self._barbers(cats)
        salon = self._salon(cats, barbers)
        self._bookings_and_reviews(customer, barbers, salon)

        self.stdout.write(self.style.SUCCESS("\nDemo data ready."))
        self.stdout.write("Accounts (password for all: %s):" % DEMO_PASSWORD)
        self.stdout.write("  Customer:      customer@nearby.local")
        self.stdout.write("  Barber:        barber1@nearby.local")
        self.stdout.write("  Salon owner:   salon@nearby.local")
        self.stdout.write("Create an admin with: python manage.py createsuperuser")

    # ------------------------------------------------------------------
    def _flush(self):
        self.stdout.write(self.style.WARNING("Flushing existing demo accounts…"))
        User.objects.filter(email__endswith="@nearby.local").delete()

    def _customer(self):
        user, created = User.objects.get_or_create(
            email="customer@nearby.local",
            defaults={"first_name": "Jamal", "last_name": "Aliyev", "role": User.Role.CUSTOMER,
                      "phone": "+994 50 111 22 33", "city": "Baku"},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _make_professional(self, email, first, last, ptype, display, city, lat, lng, *, verified=False):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": first, "last_name": last, "role": User.Role.PROFESSIONAL,
                      "phone": "+994 50 000 00 00", "city": city},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        prof = getattr(user, "professional_profile", None)
        if prof is None:
            prof = create_professional_profile(user=user, professional_type=ptype, display_name=display)
        prof.city = city
        prof.latitude = Decimal(str(lat))
        prof.longitude = Decimal(str(lng))
        prof.is_verified = verified
        prof.description = f"{display} — a demo {ptype} in {city}. Friendly service, great cuts."
        prof.public_email = email
        prof.address = f"{city} city centre"
        prof.save()
        return prof

    def _barbers(self, cats):
        specs = [
            ("barber1@nearby.local", "Rashad", "Mammadov", "Fade Studio", 0.010, 0.008, True),
            ("barber2@nearby.local", "Tural", "Hasanov", "Sharp Cuts", -0.012, 0.006, False),
            ("barber3@nearby.local", "Elvin", "Guliyev", "Classic Barber", 0.006, -0.011, True),
        ]
        barbers = []
        for email, first, last, display, dlat, dlng, verified in specs:
            prof = self._make_professional(
                email, first, last, ProfessionalProfile.ProfessionalType.BARBER,
                display, "Baku", BAKU[0] + dlat, BAKU[1] + dlng, verified=verified,
            )
            bp = prof.barber_profile
            bp.experience_years = 6
            bp.specialization = "Fades, beard trims, classic cuts"
            bp.show_price = True
            bp.price_from = Decimal("15")
            bp.save()
            self._services(prof, cats, [("Haircut", 30, 20), ("Fade", 45, 25), ("Beard", 20, 12), ("Hair + Beard", 60, 30)])
            # Portfolio/gallery images are intentionally left for the owner to
            # upload — seeding empty ImageFields would break `.url` rendering.
            barbers.append(prof)
        return barbers

    def _salon(self, cats, barbers):
        prof = self._make_professional(
            "salon@nearby.local", "Nigar", "Salon", ProfessionalProfile.ProfessionalType.SALON,
            "The Grooming Room", "Baku", BAKU[0] - 0.004, BAKU[1] + 0.012, verified=True,
        )
        sp = prof.salon_profile
        sp.number_of_workers = 4
        sp.show_price = True
        sp.price_from = Decimal("18")
        sp.save()
        self._services(prof, cats, [("Haircut", 40, 25), ("Hair Coloring", 90, 60), ("Styling", 45, 35), ("Facial", 30, 40)])
        # Add two barbers to the team.
        for barber in barbers[:2]:
            SalonMember.objects.get_or_create(
                salon=sp, barber=barber.barber_profile,
                defaults={"position": "Senior barber", "is_active": True},
            )
        # A couple of products.
        pc = ProductCategory.objects.first()
        for name, brand, price in [("Matte Clay", "Nearby Grooming", "22"), ("Beard Oil", "Nearby Grooming", "18")]:
            Product.objects.get_or_create(
                salon=sp, name=name,
                defaults={"brand": brand, "price": Decimal(price), "category": pc,
                          "description": "Demo product.", "is_available": True},
            )
        return prof

    def _services(self, prof, cats, items):
        cat_by_name = {name.lower(): cat for name, cat in cats.items()}
        for name, duration, price in items:
            Service.objects.get_or_create(
                professional=prof, name=name,
                defaults={
                    "category": cat_by_name.get(name.lower()),
                    "duration_minutes": duration,
                    "price": Decimal(str(price)),
                    "show_price": True,
                    "is_active": True,
                },
            )

    def _bookings_and_reviews(self, customer, barbers, salon):
        today = timezone.localdate()
        barber = barbers[0]
        haircut = barber.services.first()

        # A completed past booking (created directly — the engine forbids the past).
        past, _ = Booking.objects.get_or_create(
            customer=customer, professional=barber, service=haircut,
            date=today - dt.timedelta(days=7),
            defaults={
                "barber": barber.barber_profile,
                "start_time": dt.time(11, 0), "end_time": dt.time(11, 30),
                "status": BookingStatus.COMPLETED,
            },
        )
        Review.objects.get_or_create(
            booking=past,
            defaults={"customer": customer, "professional": barber, "rating": 5,
                      "comment": "Great fade, really happy with it!"},
        )
        # A couple more reviews for a nicer distribution.
        salon_service = salon.services.first()
        old_salon, _ = Booking.objects.get_or_create(
            customer=customer, professional=salon, service=salon_service,
            date=today - dt.timedelta(days=14),
            defaults={"start_time": dt.time(15, 0), "end_time": dt.time(15, 40),
                      "status": BookingStatus.COMPLETED},
        )
        Review.objects.get_or_create(
            booking=old_salon,
            defaults={"customer": customer, "professional": salon, "rating": 4,
                      "comment": "Lovely space and friendly team."},
        )
        # An upcoming pending booking.
        Booking.objects.get_or_create(
            customer=customer, professional=barber, service=haircut,
            date=today + dt.timedelta(days=2),
            defaults={"barber": barber.barber_profile,
                      "start_time": dt.time(12, 0), "end_time": dt.time(12, 30),
                      "status": BookingStatus.PENDING},
        )
