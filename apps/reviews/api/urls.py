from django.urls import path

from .views import ReviewListCreateView

app_name = "reviews_api"

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="list_create"),
]
