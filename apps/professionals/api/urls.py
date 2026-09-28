from django.urls import path

from .views import (
    NearbyProfessionalsView,
    ProfessionalDetailView,
    ProfessionalListView,
    ProfessionalServicesView,
)

app_name = "professionals_api"

urlpatterns = [
    path("", ProfessionalListView.as_view(), name="list"),
    path("nearby/", NearbyProfessionalsView.as_view(), name="nearby"),
    path("<int:pk>/", ProfessionalDetailView.as_view(), name="detail"),
    path("<int:pk>/services/", ProfessionalServicesView.as_view(), name="services"),
]
