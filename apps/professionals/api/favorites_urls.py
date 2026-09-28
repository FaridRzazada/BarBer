from django.urls import path

from .favorites import FavoriteDestroyView, FavoriteToggleView

app_name = "favorites_api"

urlpatterns = [
    path("", FavoriteToggleView.as_view(), name="toggle"),
    path("toggle/", FavoriteToggleView.as_view(), name="toggle_alt"),
    path("<int:professional_id>/", FavoriteDestroyView.as_view(), name="destroy"),
]
