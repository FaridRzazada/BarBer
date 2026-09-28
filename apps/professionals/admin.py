from django.contrib import admin

from .models import (
    BarberProfile,
    BreakTime,
    DayOff,
    Favorite,
    ProfessionalGallery,
    PortfolioImage,
    ProfessionalProfile,
    SalonMember,
    SalonProfile,
    WorkingHour,
)


class WorkingHourInline(admin.TabularInline):
    model = WorkingHour
    extra = 0


class BreakTimeInline(admin.TabularInline):
    model = BreakTime
    extra = 0


class DayOffInline(admin.TabularInline):
    model = DayOff
    extra = 0


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "professional_type", "city", "is_verified", "is_active", "created_at"]
    list_filter = ["professional_type", "is_verified", "is_active"]
    search_fields = ["display_name", "slug", "city", "user__email"]
    autocomplete_fields = ["user"]
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [WorkingHourInline, BreakTimeInline, DayOffInline]
    list_select_related = ["user"]
    actions = ["mark_verified", "mark_unverified"]

    @admin.action(description="Mark selected professionals as verified")
    def mark_verified(self, request, queryset):
        queryset.update(is_verified=True)

    @admin.action(description="Remove verified badge")
    def mark_unverified(self, request, queryset):
        queryset.update(is_verified=False)


@admin.register(BarberProfile)
class BarberProfileAdmin(admin.ModelAdmin):
    list_display = ["professional", "experience_years", "specialization", "show_price"]
    search_fields = ["professional__display_name", "specialization"]
    autocomplete_fields = ["professional"]


@admin.register(SalonProfile)
class SalonProfileAdmin(admin.ModelAdmin):
    list_display = ["professional", "number_of_workers", "show_price"]
    search_fields = ["professional__display_name"]
    autocomplete_fields = ["professional"]


@admin.register(SalonMember)
class SalonMemberAdmin(admin.ModelAdmin):
    list_display = ["salon", "barber", "position", "is_active", "joined_at"]
    list_filter = ["is_active"]
    search_fields = ["salon__professional__display_name", "barber__professional__display_name"]
    autocomplete_fields = ["salon", "barber"]


@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    list_display = ["professional", "weekday", "is_open", "start_time", "end_time"]
    list_filter = ["weekday", "is_open"]
    search_fields = ["professional__display_name"]
    autocomplete_fields = ["professional"]


@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ["professional", "date", "reason"]
    date_hierarchy = "date"
    search_fields = ["professional__display_name"]
    autocomplete_fields = ["professional"]


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ["professional", "title", "created_at"]
    search_fields = ["professional__display_name", "title"]
    autocomplete_fields = ["professional"]


@admin.register(ProfessionalGallery)
class ProfessionalGalleryAdmin(admin.ModelAdmin):
    list_display = ["professional", "title", "created_at"]
    search_fields = ["professional__display_name", "title"]
    autocomplete_fields = ["professional"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "professional", "created_at"]
    search_fields = ["user__email", "professional__display_name"]
    autocomplete_fields = ["user", "professional"]
