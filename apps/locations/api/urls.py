from django.urls import path

from .views import CityListView

app_name = "locations_api"

urlpatterns = [
    path("cities/", CityListView.as_view(), name="cities"),
]
