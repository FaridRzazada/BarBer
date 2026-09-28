from __future__ import annotations

from rest_framework import serializers

from apps.professionals.models import Favorite, ProfessionalProfile
from apps.professionals.services import is_open_now
from apps.services.api.serializers import ServiceSerializer


class ProfessionalCardSerializer(serializers.ModelSerializer):
    """Compact, privacy-safe payload for cards and map markers.

    Only public professional fields are exposed — never private ``User`` data.
    """

    name = serializers.CharField(source="display_name")
    type = serializers.CharField(source="professional_type")
    type_label = serializers.CharField(read_only=True)
    profile_image = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id",
            "name",
            "slug",
            "type",
            "type_label",
            "city",
            "latitude",
            "longitude",
            "profile_image",
            "rating",
            "review_count",
            "distance",
            "starting_price",
            "currency",
            "is_open",
            "is_verified",
            "is_favorited",
            "url",
        ]

    def get_profile_image(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get("request")
        url = obj.profile_image.url
        return request.build_absolute_uri(url) if request else url

    def get_rating(self, obj):
        avg = getattr(obj, "rating_avg", None)
        return round(avg, 1) if avg is not None else None

    def get_review_count(self, obj) -> int:
        return getattr(obj, "rating_count", 0) or 0

    def get_distance(self, obj):
        return getattr(obj, "distance_km", None)

    def get_starting_price(self, obj):
        price = obj.starting_price
        return str(price) if price is not None else None

    def get_currency(self, obj) -> str:
        from django.conf import settings

        return settings.DEFAULT_CURRENCY

    def get_is_open(self, obj) -> bool:
        return is_open_now(obj)

    def get_is_favorited(self, obj) -> bool:
        ids = self.context.get("favorited_ids")
        if ids is not None:
            return obj.id in ids
        return False


class ProfessionalDetailSerializer(ProfessionalCardSerializer):
    """Adds public contact info + services for the detail endpoint."""

    services = serializers.SerializerMethodField()

    class Meta(ProfessionalCardSerializer.Meta):
        fields = ProfessionalCardSerializer.Meta.fields + [
            "description",
            "address",
            "phone",
            "public_email",
            "website",
            "cover_image",
            "services",
        ]

    def get_services(self, obj):
        services = obj.services.filter(is_active=True).select_related("category")
        return ServiceSerializer(services, many=True, context=self.context).data


def favorited_ids_for(request) -> set[int]:
    if request and request.user.is_authenticated:
        return set(
            Favorite.objects.filter(user=request.user).values_list("professional_id", flat=True)
        )
    return set()
