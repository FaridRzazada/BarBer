"""Small, dependency-free helpers reused across apps."""
from __future__ import annotations

from django.utils.text import slugify


def unique_slugify(instance, value: str, slug_field_name: str = "slug", max_length: int | None = None) -> str:
    """Return a unique slug for ``instance`` derived from ``value``.

    Appends ``-2``, ``-3`` … only when a collision exists, and never exceeds the
    field's ``max_length``.
    """
    model = instance.__class__
    field = model._meta.get_field(slug_field_name)
    max_length = max_length or field.max_length or 50

    base = slugify(value)[:max_length].rstrip("-") or "item"
    slug = base
    counter = 2
    queryset = model._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(**{slug_field_name: slug}).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)].rstrip('-')}{suffix}"
        counter += 1
    return slug
