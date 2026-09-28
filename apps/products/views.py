from __future__ import annotations

from django.views.generic import DetailView

from .models import Product


class ProductDetailView(DetailView):
    template_name = "products/detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.select_related(
            "salon__professional__user", "category"
        ).prefetch_related("images")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["professional"] = self.object.salon.professional
        ctx["related"] = (
            Product.objects.filter(salon=self.object.salon, is_available=True)
            .exclude(pk=self.object.pk)[:4]
        )
        return ctx
