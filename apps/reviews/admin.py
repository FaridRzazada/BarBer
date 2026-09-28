from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["professional", "customer", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["professional__display_name", "customer__email", "comment"]
    autocomplete_fields = ["professional", "customer", "booking"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
