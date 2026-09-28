"""Root URL configuration.

Each feature area owns its own ``urls.py``; this module simply mounts them under
clean, human-readable prefixes and wires up media serving + error handlers.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # REST API (all endpoints live under /api/).
    path("api/", include(("config.api", "api"), namespace="api")),
    # Page routes.
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("professionals/", include("apps.professionals.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("favorites/", include("apps.professionals.favorites_urls")),
    path("messages/", include("apps.messaging.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("products/", include("apps.products.urls")),
]

# Error handlers (used when DEBUG=False).
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
