from __future__ import annotations

from django.conf import settings
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations.services import nearby_professionals
from apps.professionals.models import ProfessionalProfile
from apps.professionals.services import is_open_now
from apps.services.api.serializers import ServiceSerializer

from .serializers import (
    ProfessionalCardSerializer,
    ProfessionalDetailSerializer,
    favorited_ids_for,
)

# DB-sortable options (nearest is handled separately since it needs coordinates).
_ORDERING = {
    "newest": "-created_at",
    "rating": F("rating_avg").desc(nulls_last=True),
    "price_low": F("min_price").asc(nulls_last=True),
    "price_high": F("min_price").desc(nulls_last=True),
}


def _base_public_queryset():
    return (
        ProfessionalProfile.objects.active()
        .for_cards()
        .prefetch_related("working_hours", "break_times", "days_off")
    )


def _apply_filters(qs, params):
    professional_type = params.get("professional_type") or params.get("type")
    if professional_type in ("all", "", None):
        professional_type = None
    qs = qs.of_type(professional_type)

    city = params.get("city")
    if city:
        qs = qs.filter(city__icontains=city.strip())

    search = params.get("q") or params.get("search")
    if search:
        term = search.strip()
        qs = qs.filter(
            Q(display_name__icontains=term)
            | Q(description__icontains=term)
            | Q(city__icontains=term)
            | Q(services__name__icontains=term)
            | Q(barber_profile__specialization__icontains=term)
        ).distinct()

    service_category = params.get("service")
    if service_category:
        if str(service_category).isdigit():
            qs = qs.filter(services__category_id=service_category)
        else:
            qs = qs.filter(services__category__slug=service_category)
        qs = qs.distinct()

    if params.get("price_available") in ("1", "true", "True", "on"):
        qs = qs.filter(min_price__isnull=False)

    rating = params.get("rating")
    if rating:
        try:
            qs = qs.filter(rating_avg__gte=float(rating))
        except (TypeError, ValueError):
            pass
    return qs


class ProfessionalListView(generics.ListAPIView):
    serializer_class = ProfessionalCardSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = _apply_filters(_base_public_queryset(), self.request.query_params)
        sort = self.request.query_params.get("sort", "newest")
        ordering = _ORDERING.get(sort, "-created_at")
        return qs.order_by(ordering)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["favorited_ids"] = favorited_ids_for(self.request)
        return ctx


class ProfessionalDetailView(generics.RetrieveAPIView):
    serializer_class = ProfessionalDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return _base_public_queryset()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["favorited_ids"] = favorited_ids_for(self.request)
        return ctx


class ProfessionalServicesView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        professional = get_object_or_404(ProfessionalProfile, pk=self.kwargs["pk"])
        return professional.services.filter(is_active=True).select_related("category")


class NearbyProfessionalsView(APIView):
    """GET /api/professionals/nearby/?latitude&longitude&radius&professional_type"""

    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        latitude = self._float(params.get("latitude"), "latitude")
        longitude = self._float(params.get("longitude"), "longitude")

        radius = params.get("radius")
        try:
            radius_km = float(radius) if radius else settings.NEARBY_DEFAULT_RADIUS_KM
        except ValueError:
            radius_km = settings.NEARBY_DEFAULT_RADIUS_KM
        radius_km = max(0.5, min(radius_km, settings.NEARBY_MAX_RADIUS_KM))

        qs = _apply_filters(_base_public_queryset().locatable(), params)
        results = nearby_professionals(qs, latitude, longitude, radius_km)

        if params.get("open_now") in ("1", "true", "True", "on"):
            results = [p for p in results if is_open_now(p)]

        results = self._sort(results, params.get("sort", "nearest"))[:100]

        serializer = ProfessionalCardSerializer(
            results,
            many=True,
            context={"request": request, "favorited_ids": favorited_ids_for(request)},
        )
        return Response(
            {
                "count": len(results),
                "radius": radius_km,
                "latitude": latitude,
                "longitude": longitude,
                "results": serializer.data,
            }
        )

    @staticmethod
    def _float(value, name):
        if value is None:
            raise ValidationError({name: f"{name} is required."})
        try:
            return float(value)
        except ValueError:
            raise ValidationError({name: f"{name} must be a number."})

    @staticmethod
    def _sort(results, sort):
        if sort == "rating":
            return sorted(results, key=lambda p: (getattr(p, "rating_avg", 0) or 0), reverse=True)
        if sort == "price_low":
            return sorted(
                results,
                key=lambda p: (p.starting_price is None, p.starting_price or 0),
            )
        if sort == "price_high":
            return sorted(results, key=lambda p: (p.starting_price or 0), reverse=True)
        if sort == "newest":
            return sorted(results, key=lambda p: p.created_at, reverse=True)
        return results  # 'nearest' — already distance-sorted
