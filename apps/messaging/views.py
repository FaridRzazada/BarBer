from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class MessagesView(LoginRequiredMixin, TemplateView):
    template_name = "messages/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["initial_conversation"] = self.request.GET.get("c", "")
        return ctx
