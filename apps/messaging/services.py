"""Messaging helpers: create/find conversations and post messages."""
from __future__ import annotations

from django.utils import timezone

from apps.professionals.models import ProfessionalProfile

from .models import Conversation, Message


class MessagingError(Exception):
    pass


def get_or_create_conversation(*, customer, professional: ProfessionalProfile) -> Conversation:
    if professional.user_id == customer.id:
        raise MessagingError("You can't message your own profile.")
    conversation, _ = Conversation.objects.get_or_create(
        customer=customer, professional=professional
    )
    return conversation


def post_message(*, conversation: Conversation, sender, body: str) -> Message:
    body = (body or "").strip()
    if not body:
        raise MessagingError("Message can't be empty.")
    # Only the two participants may post.
    if sender.id not in (conversation.customer_id, conversation.professional.user_id):
        raise MessagingError("You are not part of this conversation.")

    message = Message.objects.create(conversation=conversation, sender=sender, body=body)
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])

    from apps.notifications.services import notify_new_message

    notify_new_message(message)
    return message
