from __future__ import annotations

from rest_framework import serializers

from apps.services.models import Service, ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "slug"]


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    price = serializers.SerializerMethodField()
    price_display = serializers.CharField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "duration_minutes",
            "price",
            "show_price",
            "price_display",
            "category",
            "category_name",
            "is_active",
        ]

    def get_price(self, obj):
        # Never leak a price the professional chose not to publish.
        if obj.show_price and obj.price is not None:
            return str(obj.price)
        return None
