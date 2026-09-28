from django.test import TestCase
from django.urls import reverse

from apps.professionals.models import ProfessionalProfile

from .models import CustomerProfile, User


class UserModelTests(TestCase):
    def test_create_user_defaults_to_customer(self):
        user = User.objects.create_user(email="a@example.com", password="pw")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.is_customer)

    def test_email_is_unique_and_normalised(self):
        User.objects.create_user(email="Dup@Example.com", password="pw")
        self.assertTrue(User.objects.filter(email="Dup@example.com").exists())

    def test_superuser_is_admin_role(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="pw")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertTrue(admin.is_admin_role)

    def test_customer_profile_created_by_signal(self):
        user = User.objects.create_user(email="c@example.com", password="pw", role=User.Role.CUSTOMER)
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())


class RegistrationViewTests(TestCase):
    def test_customer_registration_creates_customer(self):
        resp = self.client.post(reverse("accounts:register_customer"), {
            "first_name": "Jo", "last_name": "Doe", "email": "jo@example.com",
            "phone": "", "city": "Baku", "password1": "Str0ngPass!23", "password2": "Str0ngPass!23",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email="jo@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)

    def test_professional_registration_creates_profile(self):
        resp = self.client.post(reverse("accounts:register_professional"), {
            "professional_type": "barber", "display_name": "Fade Co",
            "first_name": "Sam", "last_name": "Lee", "email": "sam@example.com",
            "phone": "", "password1": "Str0ngPass!23", "password2": "Str0ngPass!23",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email="sam@example.com")
        self.assertEqual(user.role, User.Role.PROFESSIONAL)
        prof = ProfessionalProfile.objects.get(user=user)
        self.assertEqual(prof.professional_type, "barber")
        self.assertTrue(hasattr(prof, "barber_profile"))
        # Default working hours were created.
        self.assertEqual(prof.working_hours.count(), 7)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="taken@example.com", password="pw")
        resp = self.client.post(reverse("accounts:register_customer"), {
            "first_name": "A", "last_name": "B", "email": "taken@example.com",
            "password1": "Str0ngPass!23", "password2": "Str0ngPass!23",
        })
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertContains(resp, "already exists")

    def test_login_by_email(self):
        User.objects.create_user(email="login@example.com", password="Str0ngPass!23")
        resp = self.client.post(reverse("accounts:login"), {
            "username": "login@example.com", "password": "Str0ngPass!23",
        })
        self.assertEqual(resp.status_code, 302)
