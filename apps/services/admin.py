from django.contrib import admin

from .models import Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_active"]
    list_editable = ["order", "is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "professional", "category", "duration_minutes", "price", "show_price", "is_active"]
    list_filter = ["is_active", "show_price", "category"]
    search_fields = ["name", "professional__display_name"]
    autocomplete_fields = ["professional", "category"]
    readonly_fields = ["created_at", "updated_at"]
