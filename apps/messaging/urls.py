from django.urls import path

from .views import MessagesView

app_name = "messaging"

urlpatterns = [
    path("", MessagesView.as_view(), name="index"),
]
