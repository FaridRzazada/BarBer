from django.contrib import admin

from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "latitude", "longitude", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
