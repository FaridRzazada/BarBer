from django.urls import path

from .views import ProfessionalDetailView, ProfessionalDirectoryView

app_name = "professionals"

urlpatterns = [
    path("", ProfessionalDirectoryView.as_view(), name="list"),
    path("<slug:slug>/", ProfessionalDetailView.as_view(), name="detail"),
]
