from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sender", "body", "is_read", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "professional", "updated_at"]
    search_fields = ["customer__email", "professional__display_name"]
    autocomplete_fields = ["customer", "professional"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "sender", "is_read", "created_at"]
    list_filter = ["is_read"]
    search_fields = ["sender__email", "body"]
    autocomplete_fields = ["conversation", "sender"]
