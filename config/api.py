"""Aggregates every app's REST API routes under a single ``/api/`` namespace."""
from django.urls import include, path

urlpatterns = [
    path("professionals/", include("apps.professionals.api.urls")),
    path("services/", include("apps.services.api.urls")),
    path("bookings/", include("apps.bookings.api.urls")),
    path("reviews/", include("apps.reviews.api.urls")),
    path("favorites/", include("apps.professionals.api.favorites_urls")),
    path("notifications/", include("apps.notifications.api.urls")),
    path("messages/", include("apps.messaging.api.urls")),
    path("locations/", include("apps.locations.api.urls")),
]
