from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("find/", views.FindView.as_view(), name="find"),
    path("map/", views.MapView.as_view(), name="map"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("report/<str:target_type>/<int:target_id>/", views.ReportCreateView.as_view(), name="report"),
]
