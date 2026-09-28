from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.professionals.models import ProfessionalProfile

from ..models import Conversation
from ..services import MessagingError, get_or_create_conversation, post_message
from .serializers import ConversationSerializer, MessageSerializer


def _conversations_for(user):
    return (
        Conversation.objects.filter(Q(customer=user) | Q(professional__user=user))
        .select_related("customer", "professional__user")
        .prefetch_related("messages")
        .distinct()
    )


class MessagesRootView(APIView):
    """GET → conversations list; POST → send / start a message."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = _conversations_for(request.user)
        data = ConversationSerializer(
            conversations, many=True, context={"request": request}
        ).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        body = request.data.get("body", "")
        conversation_id = request.data.get("conversation")
        professional_id = request.data.get("professional")

        try:
            if conversation_id:
                conversation = get_object_or_404(Conversation, pk=conversation_id)
                if request.user.id not in (
                    conversation.customer_id,
                    conversation.professional.user_id,
                ):
                    raise PermissionDenied("You are not part of this conversation.")
            elif professional_id:
                if not request.user.is_customer:
                    raise MessagingError("Only customers can start a conversation.")
                professional = get_object_or_404(ProfessionalProfile, pk=professional_id)
                conversation = get_or_create_conversation(
                    customer=request.user, professional=professional
                )
            else:
                raise MessagingError("A conversation or professional is required.")

            message = post_message(conversation=conversation, sender=request.user, body=body)
        except MessagingError as exc:
            return Response(
                {"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "success": True,
                "conversation": conversation.id,
                "message": MessageSerializer(message, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if request.user.id not in (
            conversation.customer_id,
            conversation.professional.user_id,
        ):
            raise PermissionDenied("You are not part of this conversation.")

        # Mark the other party's messages as read.
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(
            is_read=True
        )
        messages = conversation.messages.select_related("sender").all()
        data = MessageSerializer(messages, many=True, context={"request": request}).data
        return Response(
            {
                "conversation": conversation.id,
                "other_name": ConversationSerializer(
                    conversation, context={"request": request}
                ).get_other_name(conversation),
                "results": data,
            }
        )
