"""Booking pages: history, detail (with no-JS status/review actions) and the
booking wizard. AJAX drives the happy path; POST fallbacks keep it usable
without JavaScript and make the flow easy to test."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, TemplateView, View

from apps.professionals.models import ProfessionalProfile, SalonMember
from apps.reviews.forms import ReviewForm
from apps.reviews.services import ReviewError, create_review

from .models import Booking, BookingStatus
from .services import (
    BookingError,
    cancel_booking,
    complete_booking,
    confirm_booking,
    mark_no_show,
)


class BookingHistoryView(LoginRequiredMixin, TemplateView):
    template_name = "bookings/history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = (
            Booking.objects.for_customer(self.request.user)
            .select_related("professional", "service", "barber__professional")
        )
        ctx["upcoming"] = [b for b in qs if b.is_active and not b.is_past]
        ctx["completed"] = qs.filter(status=BookingStatus.COMPLETED)
        ctx["cancelled"] = qs.filter(status=BookingStatus.CANCELLED)
        ctx["no_show"] = qs.filter(status=BookingStatus.NO_SHOW)
        return ctx


class BookingDetailView(LoginRequiredMixin, DetailView):
    template_name = "bookings/detail.html"
    context_object_name = "booking"

    def get_queryset(self):
        return Booking.objects.select_related(
            "professional__user", "service", "customer", "barber__professional"
        )

    def get_object(self, queryset=None):
        booking = super().get_object(queryset)
        user = self.request.user
        self.is_customer_owner = booking.customer_id == user.id
        self.is_pro_owner = booking.professional.user_id == user.id
        if not (self.is_customer_owner or self.is_pro_owner or user.is_staff):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return booking

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_customer_owner"] = self.is_customer_owner
        ctx["is_pro_owner"] = self.is_pro_owner
        if self.object.can_be_reviewed and self.is_customer_owner:
            ctx["review_form"] = ReviewForm()
        return ctx

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        action = request.POST.get("action")
        try:
            if action == "cancel":
                cancel_booking(booking, by_customer=self.is_customer_owner and not self.is_pro_owner)
                messages.success(request, "Booking cancelled.")
            elif action == "confirm" and self.is_pro_owner:
                confirm_booking(booking)
                messages.success(request, "Booking confirmed.")
            elif action == "complete" and self.is_pro_owner:
                complete_booking(booking)
                messages.success(request, "Booking marked as completed.")
            elif action == "no_show" and self.is_pro_owner:
                mark_no_show(booking)
                messages.success(request, "Booking marked as no-show.")
            elif action == "review" and self.is_customer_owner:
                form = ReviewForm(request.POST)
                if form.is_valid():
                    create_review(
                        customer=request.user,
                        booking=booking,
                        rating=form.cleaned_data["rating"],
                        comment=form.cleaned_data["comment"],
                    )
                    messages.success(request, "Thanks for your review!")
                else:
                    messages.error(request, "Please choose a rating.")
            else:
                messages.error(request, "That action isn't allowed.")
        except (BookingError, ReviewError) as exc:
            messages.error(request, str(exc))
        return redirect("bookings:detail", pk=booking.pk)


class BookingCreateView(LoginRequiredMixin, TemplateView):
    template_name = "bookings/create.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_customer:
            messages.info(request, "Only customer accounts can book appointments.")
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        professional = get_object_or_404(
            ProfessionalProfile.objects.active().select_related("salon_profile", "barber_profile"),
            pk=self.request.GET.get("professional"),
        )
        ctx["professional"] = professional
        ctx["services"] = professional.services.filter(is_active=True).select_related("category")
        if professional.is_salon and hasattr(professional, "salon_profile"):
            ctx["team"] = (
                SalonMember.objects.filter(salon=professional.salon_profile, is_active=True)
                .select_related("barber__professional")
            )
        else:
            ctx["team"] = []
        ctx["preselect_service"] = self.request.GET.get("service", "")
        ctx["preselect_barber"] = self.request.GET.get("barber", "")
        return ctx
