from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.services.models import ServiceCategory

from .serializers import ServiceCategorySerializer


class ServiceCategoryListView(generics.ListAPIView):
    """Public service taxonomy (used by filters and 'Popular services')."""

    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            ServiceCategory.objects.filter(is_active=True)
            .annotate(
                service_count=Count(
                    "services", filter=Q(services__is_active=True), distinct=True
                )
            )
            .order_by("order", "name")
        )
