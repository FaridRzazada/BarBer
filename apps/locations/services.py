"""Geographic distance utilities.

Strategy (scalable and PostGIS-ready): use an indexed latitude/longitude
*bounding box* to cheaply discard far-away rows in the database, then compute the
exact great-circle (Haversine) distance in Python only for the small candidate
set. When the project later moves to PostGIS, ``nearby_professionals`` is the one
function to swap for a ``ST_DWithin`` query — callers stay unchanged.
"""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    r_lat1, r_lat2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """(min_lat, max_lat, min_lng, max_lng) that fully contains the radius circle."""
    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    # Guard against division by ~0 near the poles.
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    lng_delta = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))
    return (lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta)


def nearby_professionals(queryset, lat: float, lng: float, radius_km: float):
    """Return a distance-sorted list of professionals within ``radius_km``.

    Each returned object gets a ``distance_km`` attribute (rounded to 1 dp).
    ``queryset`` should already be filtered to locatable, active professionals and
    annotated for cards (rating/price) by the caller.
    """
    min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
    candidates = queryset.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lng,
        longitude__lte=max_lng,
    )

    results = []
    for pro in candidates:
        distance = haversine_km(lat, lng, float(pro.latitude), float(pro.longitude))
        if distance <= radius_km:
            pro.distance_km = round(distance, 1)
            results.append(pro)
    results.sort(key=lambda p: p.distance_km)
    return results
