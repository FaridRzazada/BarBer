"""View mixins for role-gated pages (server-side authorization)."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class CustomerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self) -> bool:
        return self.request.user.is_customer


class ProfessionalRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require a professional account *and* attach ``self.professional``."""

    def test_func(self) -> bool:
        return self.request.user.is_professional and hasattr(
            self.request.user, "professional_profile"
        )

    @property
    def professional(self):
        return self.request.user.professional_profile
