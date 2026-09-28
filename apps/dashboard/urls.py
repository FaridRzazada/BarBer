from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("profile/setup/", views.profile_setup, name="profile_setup"),
    path("appointments/", views.appointments, name="appointments"),
    path("calendar/", views.calendar, name="calendar"),
    # Services
    path("services/", views.services, name="services"),
    path("services/<int:pk>/edit/", views.service_edit, name="service_edit"),
    path("services/<int:pk>/delete/", views.service_delete, name="service_delete"),
    # Availability
    path("hours/", views.hours, name="hours"),
    # Media
    path("portfolio/", views.portfolio, name="portfolio"),
    path("portfolio/<int:pk>/delete/", views.portfolio_delete, name="portfolio_delete"),
    path("gallery/", views.gallery, name="gallery"),
    path("gallery/<int:pk>/delete/", views.gallery_delete, name="gallery_delete"),
    # Products (salon)
    path("products/", views.products, name="products"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # Team (salon)
    path("team/", views.team, name="team"),
    # Reviews
    path("reviews/", views.reviews, name="reviews"),
    # Settings
    path("settings/", views.settings_view, name="settings"),
    # Redirects to the canonical top-level pages
    path("messages/", views.DashboardMessagesRedirect.as_view(), name="messages"),
    path("notifications/", views.DashboardNotificationsRedirect.as_view(), name="notifications"),
]
