"""Admin configuration for accounts."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomerProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-created_at"]
    list_display = [
        "email",
        "get_full_name",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "created_at",
    ]
    list_filter = ["role", "is_verified", "is_active", "is_staff", "gender"]
    search_fields = ["email", "first_name", "last_name", "phone", "username"]
    readonly_fields = ["created_at", "updated_at", "last_login", "date_joined"]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {
            "fields": (
                "first_name", "last_name", "phone", "avatar",
                "date_of_birth", "gender", "city",
            )
        }),
        (_("Role & status"), {"fields": ("role", "is_verified")}),
        (_("Permissions"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "city", "gender", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "city"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
