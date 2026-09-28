from django.urls import path

from .views import NotificationsView

app_name = "notifications"

urlpatterns = [
    path("", NotificationsView.as_view(), name="index"),
]
