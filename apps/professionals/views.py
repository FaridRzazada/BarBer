"""Public professional directory, detail page and favorites page."""
from __future__ import annotations

from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from apps.reviews.models import Review
from apps.reviews.services import rating_summary
from apps.services.models import ServiceCategory

from .models import Favorite, ProfessionalProfile, SalonMember, Weekday
from .services import is_open_now


class ProfessionalDirectoryView(ListView):
    """Server-rendered, paginated directory (SEO + no-JS fallback)."""

    template_name = "professionals/list.html"
    context_object_name = "professionals"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            ProfessionalProfile.objects.active()
            .for_cards()
            .prefetch_related("working_hours", "break_times", "days_off")
        )
        params = self.request.GET
        qs = qs.of_type(params.get("type"))
        if params.get("city"):
            qs = qs.filter(city__icontains=params["city"].strip())
        if params.get("q"):
            term = params["q"].strip()
            qs = qs.filter(
                Q(display_name__icontains=term)
                | Q(description__icontains=term)
                | Q(services__name__icontains=term)
            ).distinct()
        return qs.order_by("-is_verified", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        favorited = set()
        if self.request.user.is_authenticated:
            favorited = set(
                Favorite.objects.filter(user=self.request.user).values_list(
                    "professional_id", flat=True
                )
            )
        for pro in ctx["professionals"]:
            pro.is_open = is_open_now(pro)
            pro.is_favorited = pro.id in favorited
        ctx["categories"] = ServiceCategory.objects.filter(is_active=True)
        ctx["current_type"] = self.request.GET.get("type", "all")
        ctx["current_query"] = self.request.GET.get("q", "")
        ctx["current_city"] = self.request.GET.get("city", "")
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class ProfessionalDetailView(DetailView):
    template_name = "professionals/detail.html"
    context_object_name = "professional"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            ProfessionalProfile.objects.active()
            .select_related("user", "barber_profile", "salon_profile")
            .prefetch_related(
                "working_hours",
                "break_times",
                "days_off",
                "portfolio_images",
                "gallery_images",
                "services__category",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pro = self.object

        # Services grouped by category (stable ordering).
        grouped: dict = defaultdict(list)
        for service in pro.services.filter(is_active=True):
            grouped[service.category.name if service.category else "Other"].append(service)
        ctx["services_by_category"] = dict(grouped)
        ctx["has_services"] = any(grouped.values())

        # Working hours for all 7 days (fill gaps as closed).
        hours = {wh.weekday: wh for wh in pro.working_hours.all()}
        ctx["week_hours"] = [(label, hours.get(value)) for value, label in Weekday.choices]

        ctx["portfolio_images"] = pro.portfolio_images.all()
        ctx["gallery_images"] = pro.gallery_images.all()

        ctx["reviews"] = (
            Review.objects.filter(professional=pro)
            .select_related("customer", "booking__service")[:10]
        )
        ctx["rating"] = rating_summary(pro)

        if pro.is_salon and hasattr(pro, "salon_profile"):
            ctx["products"] = pro.salon_profile.products.filter(is_available=True)[:12]
            ctx["team"] = (
                SalonMember.objects.filter(salon=pro.salon_profile, is_active=True)
                .select_related("barber__professional__user")
            )
        else:
            ctx["products"] = []
            ctx["team"] = []

        ctx["is_open"] = is_open_now(pro)
        ctx["is_favorited"] = (
            self.request.user.is_authenticated
            and Favorite.objects.filter(user=self.request.user, professional=pro).exists()
        )
        ctx["meta_description"] = (
            (pro.description[:155] + "…")
            if pro.description
            else f"Book {pro.display_name}, a {pro.type_label.lower()} on Nearby."
        )
        return ctx


class FavoritesView(LoginRequiredMixin, TemplateView):
    template_name = "professionals/favorites.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pros = list(
            ProfessionalProfile.objects.filter(favorited_by__user=self.request.user)
            .for_cards()
            .prefetch_related("working_hours", "break_times", "days_off")
            .order_by("-favorited_by__created_at")
        )
        for pro in pros:
            pro.is_open = is_open_now(pro)
            pro.is_favorited = True
        ctx["professionals"] = pros
        return ctx
