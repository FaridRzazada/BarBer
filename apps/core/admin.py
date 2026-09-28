from django.contrib import admin

from .models import ContactMessage, Report


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "name", "email", "is_handled", "created_at"]
    list_filter = ["is_handled"]
    search_fields = ["subject", "name", "email", "message"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "target_type", "target_id", "reason", "status", "reporter", "created_at"]
    list_filter = ["status", "target_type", "reason"]
    search_fields = ["description", "reporter__email"]
    autocomplete_fields = ["reporter"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "updated_at"]
    actions = ["mark_resolved", "mark_rejected"]

    @admin.action(description="Mark selected reports resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(status=Report.Status.RESOLVED)

    @admin.action(description="Mark selected reports rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(status=Report.Status.REJECTED)
