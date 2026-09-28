from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Notification


class NotificationsView(LoginRequiredMixin, ListView):
    template_name = "notifications/index.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        qs = Notification.objects.for_user(self.request.user)
        if self.request.GET.get("filter") == "unread":
            qs = qs.unread()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_filter"] = self.request.GET.get("filter", "all")
        ctx["unread_count"] = Notification.objects.for_user(self.request.user).unread().count()
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx
