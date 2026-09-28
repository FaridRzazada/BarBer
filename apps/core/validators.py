"""Server-side image validation shared by forms and DRF serializers.

We never trust the client: extension, reported content type and size are all
checked, and ``ImageField`` additionally verifies the payload really is an image
(Pillow) when the model/form field is cleaned.
"""
from __future__ import annotations

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image_file(uploaded) -> None:
    """Validate an uploaded image's extension, content type and size."""
    max_bytes = settings.IMAGE_MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded.size and uploaded.size > max_bytes:
        raise ValidationError(
            _("Image is too large (max %(mb)s MB).") % {"mb": settings.IMAGE_MAX_UPLOAD_SIZE_MB}
        )

    ext = os.path.splitext(uploaded.name)[1].lower().lstrip(".")
    if ext not in settings.IMAGE_ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("Unsupported file type '.%(ext)s'. Allowed: %(allowed)s.")
            % {"ext": ext, "allowed": ", ".join(settings.IMAGE_ALLOWED_EXTENSIONS)}
        )

    content_type = getattr(uploaded, "content_type", None)
    if content_type and content_type not in settings.IMAGE_ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            _("Unsupported content type '%(ct)s'.") % {"ct": content_type}
        )
