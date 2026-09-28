"""Authentication & registration views."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from apps.professionals.services import create_professional_profile

from .forms import (
    CustomerRegistrationForm,
    EmailAuthenticationForm,
    ProfessionalRegistrationForm,
)


class RedirectAuthenticatedMixin:
    """Send already-logged-in users to their dashboard."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)


class RegisterChoiceView(RedirectAuthenticatedMixin, TemplateView):
    template_name = "accounts/register.html"


class CustomerRegisterView(RedirectAuthenticatedMixin, FormView):
    template_name = "accounts/register_customer.html"
    form_class = CustomerRegistrationForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="apps.accounts.backends.EmailOrUsernameModelBackend")
        messages.success(self.request, _("Welcome to Nearby! Your account is ready."))
        return super().form_valid(form)


class ProfessionalRegisterView(RedirectAuthenticatedMixin, FormView):
    template_name = "accounts/register_professional.html"
    form_class = ProfessionalRegistrationForm

    def form_valid(self, form):
        user = form.save()
        create_professional_profile(
            user=user,
            professional_type=form.cleaned_data["professional_type"],
            display_name=form.cleaned_data["display_name"],
        )
        login(self.request, user, backend="apps.accounts.backends.EmailOrUsernameModelBackend")
        messages.success(
            self.request,
            _("Your professional account is ready. Let's set up your profile."),
        )
        return redirect("dashboard:profile_setup")


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember = form.cleaned_data.get("remember_me")
        # No "remember me" -> session cookie expires when the browser closes.
        self.request.session.set_expiry(0 if not remember else 60 * 60 * 24 * 14)
        return super().form_valid(form)
