from __future__ import annotations

from rest_framework import serializers

from ..models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    is_mine = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "body", "is_mine", "sender_name", "is_read", "created_at"]

    def get_is_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)


class ConversationSerializer(serializers.ModelSerializer):
    other_name = serializers.SerializerMethodField()
    other_url = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_time = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_name",
            "other_url",
            "last_message",
            "last_time",
            "unread_count",
            "updated_at",
        ]

    def _is_customer_side(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.id == obj.customer_id)

    def get_other_name(self, obj) -> str:
        if self._is_customer_side(obj):
            return obj.professional.display_name
        return obj.customer.display_name

    def get_other_url(self, obj):
        if self._is_customer_side(obj):
            return obj.professional.get_absolute_url()
        return None

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.body[:80] if last else ""

    def get_last_time(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.created_at if last else obj.updated_at

    def get_unread_count(self, obj) -> int:
        request = self.context.get("request")
        if not request:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
