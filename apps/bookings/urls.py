from django.urls import path

from .views import BookingCreateView, BookingDetailView, BookingHistoryView

app_name = "bookings"

urlpatterns = [
    path("", BookingHistoryView.as_view(), name="history"),
    path("new/", BookingCreateView.as_view(), name="create"),
    path("<int:pk>/", BookingDetailView.as_view(), name="detail"),
]
