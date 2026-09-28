from __future__ import annotations

from rest_framework import serializers

from ..models import Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    service_name = serializers.CharField(source="booking.service.name", default=None, read_only=True)

    class Meta:
        model = Review
        fields = ["id", "customer_name", "service_name", "rating", "comment", "created_at"]


class ReviewCreateSerializer(serializers.Serializer):
    booking = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
