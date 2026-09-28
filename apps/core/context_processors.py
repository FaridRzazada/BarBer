"""Template context processors for site-wide values."""
from __future__ import annotations

from django.conf import settings


def site_globals(request) -> dict:
    """Expose branding + map defaults to every template."""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "DEFAULT_CURRENCY": settings.DEFAULT_CURRENCY,
        "MAP_DEFAULT_LAT": settings.MAP_DEFAULT_LAT,
        "MAP_DEFAULT_LNG": settings.MAP_DEFAULT_LNG,
        "MAP_DEFAULT_ZOOM": settings.MAP_DEFAULT_ZOOM,
        "NEARBY_DEFAULT_RADIUS_KM": settings.NEARBY_DEFAULT_RADIUS_KM,
    }
