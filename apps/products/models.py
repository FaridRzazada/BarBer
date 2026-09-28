"""Salon product catalogue.

This is a *catalogue only* — no cart, checkout or payments (by design). Products
belong to salons; the backend enforces that a barber cannot own products.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.uploads import product_image_upload_to
from apps.core.utils import unique_slugify
from apps.core.validators import validate_image_file


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("product category")
        verbose_name_plural = _("product categories")
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    salon = models.ForeignKey(
        "professionals.SalonProfile", on_delete=models.CASCADE, related_name="products"
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default=settings.DEFAULT_CURRENCY)
    stock = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    main_image = models.ImageField(
        upload_to=product_image_upload_to,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["salon", "is_available"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def price_display(self) -> str | None:
        if self.price is None:
            return None
        return f"{self.price:g} {self.currency}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to=product_image_upload_to, validators=[validate_image_file]
    )
    title = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = _("product image")
        verbose_name_plural = _("product images")
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.title or f"Image #{self.pk}"
