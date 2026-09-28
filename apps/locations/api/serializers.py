from __future__ import annotations

from rest_framework import serializers

from ..models import City


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "latitude", "longitude"]
