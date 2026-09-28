from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "professional", "service", "date", "start_time", "status"]
    list_filter = ["status", "date"]
    search_fields = ["customer__email", "professional__display_name", "service__name"]
    autocomplete_fields = ["customer", "professional", "barber", "service"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at", "end_time"]
    list_select_related = ["customer", "professional", "service"]
