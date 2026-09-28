from __future__ import annotations

from rest_framework import serializers

from apps.professionals.models import BarberProfile, ProfessionalProfile
from apps.services.models import Service

from ..models import Booking


class AvailableSlotSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    available = serializers.BooleanField()


class BookingCreateSerializer(serializers.Serializer):
    professional = serializers.PrimaryKeyRelatedField(
        queryset=ProfessionalProfile.objects.active()
    )
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    barber = serializers.PrimaryKeyRelatedField(
        queryset=BarberProfile.objects.all(), required=False, allow_null=True
    )
    date = serializers.DateField()
    start_time = serializers.TimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BookingSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.display_name", read_only=True)
    professional_slug = serializers.CharField(source="professional.slug", read_only=True)
    professional_url = serializers.CharField(source="professional.get_absolute_url", read_only=True)
    barber_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="service.name", read_only=True)
    duration_minutes = serializers.IntegerField(source="service.duration_minutes", read_only=True)
    price_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    can_customer_cancel = serializers.BooleanField(read_only=True)
    can_be_reviewed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "professional",
            "professional_name",
            "professional_slug",
            "professional_url",
            "barber",
            "barber_name",
            "service",
            "service_name",
            "duration_minutes",
            "price_display",
            "date",
            "start_time",
            "end_time",
            "status",
            "status_display",
            "notes",
            "customer_name",
            "customer_phone",
            "can_customer_cancel",
            "can_be_reviewed",
            "created_at",
        ]
        read_only_fields = fields

    def get_barber_name(self, obj):
        if obj.barber:
            return obj.barber.professional.display_name
        return None

    def get_price_display(self, obj):
        service = obj.service
        if service.show_price and service.price is not None:
            from django.conf import settings

            return f"{service.price:g} {settings.DEFAULT_CURRENCY}"
        return None
