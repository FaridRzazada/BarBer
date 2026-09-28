from django.urls import path

from .views import FavoritesView

app_name = "favorites"

urlpatterns = [
    path("", FavoritesView.as_view(), name="index"),
]
