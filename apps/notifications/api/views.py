from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.for_user(request.user)
        if request.query_params.get("unread") in ("1", "true", "True"):
            qs = qs.unread()
        qs = qs[:50]
        data = NotificationSerializer(qs, many=True).data
        return Response(
            {
                "count": len(data),
                "unread": Notification.objects.for_user(request.user).unread().count(),
                "results": data,
            }
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response({"success": True, "id": notification.id, "redirect": notification.url})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.for_user(request.user).unread().update(is_read=True)
        return Response({"success": True})


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.for_user(request.user).unread().count()
        return Response({"count": count})
