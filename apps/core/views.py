"""Public site pages + error handlers."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, TemplateView

from apps.locations.models import City
from apps.professionals.models import ProfessionalProfile
from apps.services.models import ServiceCategory

from .forms import ContactForm, ReportForm
from .models import Report


class HomeView(TemplateView):
    template_name = "home/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = ProfessionalProfile.objects.active().for_cards().prefetch_related(
            "working_hours", "break_times", "days_off"
        )
        ctx["featured_salons"] = list(
            base.filter(professional_type=ProfessionalProfile.ProfessionalType.SALON)
            .order_by("-is_verified", "-created_at")[:6]
        )
        ctx["recent_professionals"] = list(base.order_by("-created_at")[:8])
        ctx["popular_services"] = list(
            ServiceCategory.objects.filter(is_active=True)
            .annotate(service_count=Count("services", filter=Q(services__is_active=True)))
            .order_by("-service_count", "order")[:8]
        )
        ctx["cities"] = City.objects.filter(is_active=True)
        return ctx


class FindView(TemplateView):
    """Directory + map. Results are loaded by the front-end via the API."""

    template_name = "professionals/find.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ServiceCategory.objects.filter(is_active=True).order_by("order", "name")
        ctx["cities"] = City.objects.filter(is_active=True)
        ctx["initial_query"] = self.request.GET.get("q", "")
        ctx["initial_city"] = self.request.GET.get("city", "")
        ctx["initial_type"] = self.request.GET.get("type", "all")
        return ctx


class MapView(FindView):
    template_name = "professionals/map.html"


class AboutView(TemplateView):
    template_name = "core/about.html"


class ContactView(CreateView):
    template_name = "core/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("core:contact")

    def form_valid(self, form):
        messages.success(self.request, _("Thanks for reaching out — we'll get back to you soon."))
        return super().form_valid(form)


class ReportCreateView(LoginRequiredMixin, View):
    """Let a logged-in user report a professional, review or message."""

    template_name = "core/report.html"

    def _valid_target(self, target_type: str) -> bool:
        return target_type in Report.TargetType.values

    def get(self, request, target_type, target_id):
        if not self._valid_target(target_type):
            messages.error(request, _("Unknown report target."))
            return redirect("core:home")
        return render(request, self.template_name, {
            "form": ReportForm(), "target_type": target_type, "target_id": target_id,
        })

    def post(self, request, target_type, target_id):
        if not self._valid_target(target_type):
            messages.error(request, _("Unknown report target."))
            return redirect("core:home")
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_type = target_type
            report.target_id = target_id
            report.save()
            messages.success(request, _("Thanks for the report. Our team will review it."))
            return redirect("core:home")
        return render(request, self.template_name, {
            "form": form, "target_type": target_type, "target_id": target_id,
        })


# --- Error handlers -------------------------------------------------------
def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    # Render without a request context so context processors (which may touch the
    # DB) can't fail again while we're already handling a server error.
    from django.http import HttpResponseServerError
    from django.template import loader

    return HttpResponseServerError(loader.get_template("errors/500.html").render({}))
