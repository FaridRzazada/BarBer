from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

app_name = "notifications_api"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread_count"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="read_all"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="mark_read"),
]
