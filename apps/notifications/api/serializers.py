from __future__ import annotations

from django.utils.timesince import timesince
from rest_framework import serializers

from ..models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time_since = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "url",
            "is_read",
            "created_at",
            "time_since",
        ]

    def get_time_since(self, obj) -> str:
        return f"{timesince(obj.created_at)} ago"
