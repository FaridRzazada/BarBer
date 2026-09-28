from django.urls import path

from .views import AvailableSlotsView, BookingDetailView, BookingListCreateView

app_name = "bookings_api"

urlpatterns = [
    path("available-slots/", AvailableSlotsView.as_view(), name="available_slots"),
    path("", BookingListCreateView.as_view(), name="list_create"),
    path("<int:pk>/", BookingDetailView.as_view(), name="detail"),
]
