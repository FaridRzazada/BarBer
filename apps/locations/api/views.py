from __future__ import annotations

from rest_framework import generics
from rest_framework.permissions import AllowAny

from ..models import City
from .serializers import CitySerializer


class CityListView(generics.ListAPIView):
    """Public city list used for search-by-city and centring the map."""

    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = City.objects.filter(is_active=True)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q.strip())
        return qs
