import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.services.models import Service

from .models import Favorite, ProfessionalProfile
from .services import compute_profile_completion, create_professional_profile, is_open_now


def make_pro(email, ptype="barber", name="Pro", lat=None, lng=None, active=True):
    user = User.objects.create_user(email=email, password="pw", role=User.Role.PROFESSIONAL)
    prof = create_professional_profile(user=user, professional_type=ptype, display_name=name)
    if lat is not None:
        prof.latitude = Decimal(str(lat))
        prof.longitude = Decimal(str(lng))
    prof.is_active = active
    prof.save()
    return prof


class OpenStatusTests(TestCase):
    def setUp(self):
        self.pro = make_pro("p@example.com")

    def test_open_during_working_hours(self):
        # Wednesday 10:00 — default hours are 09:00–19:00.
        wednesday = self._next_weekday(2)
        at = timezone.make_aware(dt.datetime.combine(wednesday, dt.time(10, 0)))
        self.assertTrue(is_open_now(self.pro, at=at))

    def test_closed_outside_hours(self):
        wednesday = self._next_weekday(2)
        at = timezone.make_aware(dt.datetime.combine(wednesday, dt.time(22, 0)))
        self.assertFalse(is_open_now(self.pro, at=at))

    def test_closed_on_sunday(self):
        sunday = self._next_weekday(6)
        at = timezone.make_aware(dt.datetime.combine(sunday, dt.time(12, 0)))
        self.assertFalse(is_open_now(self.pro, at=at))

    def _next_weekday(self, weekday):
        base = timezone.localdate()
        return base + dt.timedelta(days=(weekday - base.weekday()) % 7)


class CompletionTests(TestCase):
    def test_completion_increases_with_more_info(self):
        pro = make_pro("c@example.com")
        before = compute_profile_completion(pro)["percent"]
        pro.description = "We do great fades."
        pro.latitude, pro.longitude = Decimal("40.4"), Decimal("49.8")
        pro.phone = "+994 50"
        pro.save()
        Service.objects.create(professional=pro, name="Cut", duration_minutes=30)
        after = compute_profile_completion(pro)["percent"]
        self.assertGreater(after, before)
        self.assertLessEqual(after, 100)


class NearbyApiTests(TestCase):
    def setUp(self):
        # Close (~1.5km) and far (~well outside 5km) professionals.
        self.near = make_pro("near@example.com", name="Near", lat=40.4093, lng=49.8671)
        self.far = make_pro("far@example.com", name="Far", lat=40.60, lng=49.60)

    def test_nearby_returns_within_radius_sorted(self):
        resp = self.client.get("/api/professionals/nearby/", {
            "latitude": 40.4093, "longitude": 49.8671, "radius": 5,
        })
        self.assertEqual(resp.status_code, 200)
        names = [r["name"] for r in resp.json()["results"]]
        self.assertIn("Near", names)
        self.assertNotIn("Far", names)

    def test_nearby_requires_coordinates(self):
        resp = self.client.get("/api/professionals/nearby/")
        self.assertEqual(resp.status_code, 400)

    def test_inactive_professional_hidden(self):
        make_pro("hidden@example.com", name="Hidden", lat=40.4093, lng=49.8671, active=False)
        resp = self.client.get("/api/professionals/nearby/", {"latitude": 40.4093, "longitude": 49.8671, "radius": 5})
        names = [r["name"] for r in resp.json()["results"]]
        self.assertNotIn("Hidden", names)


class SearchApiTests(TestCase):
    def test_search_by_name(self):
        make_pro("s1@example.com", name="Fade Masters")
        make_pro("s2@example.com", name="Colour Bar")
        resp = self.client.get("/api/professionals/", {"q": "fade"})
        names = [r["name"] for r in resp.json()["results"]]
        self.assertIn("Fade Masters", names)
        self.assertNotIn("Colour Bar", names)

    def test_filter_by_type(self):
        make_pro("b@example.com", ptype="barber", name="A Barber")
        make_pro("sal@example.com", ptype="salon", name="A Salon")
        resp = self.client.get("/api/professionals/", {"professional_type": "salon"})
        names = [r["name"] for r in resp.json()["results"]]
        self.assertEqual(names, ["A Salon"])


class FavoriteApiTests(TestCase):
    def test_toggle_favorite(self):
        pro = make_pro("fav@example.com")
        customer = User.objects.create_user(email="cust@example.com", password="pw", role=User.Role.CUSTOMER)
        self.client.force_login(customer)
        r1 = self.client.post("/api/favorites/", {"professional": pro.id}, content_type="application/json")
        self.assertTrue(r1.json()["favorited"])
        self.assertTrue(Favorite.objects.filter(user=customer, professional=pro).exists())
        r2 = self.client.post("/api/favorites/", {"professional": pro.id}, content_type="application/json")
        self.assertFalse(r2.json()["favorited"])

    def test_favorite_requires_login(self):
        pro = make_pro("fav2@example.com")
        resp = self.client.post("/api/favorites/", {"professional": pro.id}, content_type="application/json")
        self.assertIn(resp.status_code, (401, 403))
