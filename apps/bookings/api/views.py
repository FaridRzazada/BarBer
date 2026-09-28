from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.professionals.models import ProfessionalProfile
from apps.services.models import Service

from ..models import Booking, BookingStatus
from ..services import (
    BookingError,
    cancel_booking,
    complete_booking,
    confirm_booking,
    create_booking,
    get_available_slots,
    mark_no_show,
)
from .serializers import BookingCreateSerializer, BookingSerializer


class AvailableSlotsView(APIView):
    """GET /api/bookings/available-slots/?professional&service&date&barber"""

    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        professional = get_object_or_404(
            ProfessionalProfile.objects.active(), pk=params.get("professional")
        )
        service = get_object_or_404(
            Service, pk=params.get("service"), professional=professional
        )
        date_str = params.get("date")
        from django.utils.dateparse import parse_date

        date = parse_date(date_str) if date_str else None
        if date is None:
            return Response(
                {"success": False, "error": "A valid date (YYYY-MM-DD) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        barber = None
        barber_id = params.get("barber")
        if barber_id and str(barber_id).isdigit():
            from apps.professionals.models import BarberProfile

            barber = BarberProfile.objects.filter(pk=barber_id).first()

        slots = get_available_slots(professional, service, date, barber=barber)
        return Response(
            {
                "professional": professional.id,
                "service": service.id,
                "date": date.isoformat(),
                "slots": [s.as_dict() for s in slots],
            }
        )


class BookingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Booking.objects.select_related(
            "professional", "service", "barber__professional", "customer"
        )
        if user.is_professional and hasattr(user, "professional_profile"):
            qs = qs.for_professional(user.professional_profile)
        else:
            qs = qs.for_customer(user)

        status_filter = request.query_params.get("status")
        if status_filter in BookingStatus.values:
            qs = qs.filter(status=status_filter)

        data = BookingSerializer(qs, many=True, context={"request": request}).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        if not request.user.is_customer:
            return Response(
                {"success": False, "error": "Only customers can create bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            booking = create_booking(
                customer=request.user,
                professional=vd["professional"],
                service=vd["service"],
                date=vd["date"],
                start_time=vd["start_time"],
                barber=vd.get("barber"),
                notes=vd.get("notes", ""),
            )
        except BookingError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": True,
                "booking_id": booking.id,
                "message": "Booking created successfully.",
                "booking": BookingSerializer(booking, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_owned(self, request, pk) -> Booking:
        booking = get_object_or_404(
            Booking.objects.select_related("professional", "service", "customer", "barber__professional"),
            pk=pk,
        )
        user = request.user
        is_customer_owner = booking.customer_id == user.id
        is_pro_owner = booking.professional.user_id == user.id
        if not (is_customer_owner or is_pro_owner or user.is_staff):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You don't have access to this booking.")
        booking._is_customer_owner = is_customer_owner
        booking._is_pro_owner = is_pro_owner
        return booking

    def get(self, request, pk):
        booking = self._get_owned(request, pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)

    def patch(self, request, pk):
        booking = self._get_owned(request, pk)
        target = request.data.get("status")
        try:
            self._change_status(booking, target)
        except BookingError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"success": True, "booking": BookingSerializer(booking, context={"request": request}).data}
        )

    def delete(self, request, pk):
        # DELETE cancels a booking (we never hard-delete history).
        booking = self._get_owned(request, pk)
        try:
            cancel_booking(booking, by_customer=booking._is_customer_owner)
        except BookingError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "message": "Booking cancelled."})

    def _change_status(self, booking, target):
        if target not in BookingStatus.values:
            raise BookingError("Unknown status.")
        if booking._is_customer_owner and not booking._is_pro_owner:
            # Customers may only cancel.
            if target != BookingStatus.CANCELLED:
                raise BookingError("Customers can only cancel a booking.")
            cancel_booking(booking, by_customer=True)
            return
        # Professional actions.
        if target == BookingStatus.CONFIRMED:
            confirm_booking(booking)
        elif target == BookingStatus.COMPLETED:
            complete_booking(booking)
        elif target == BookingStatus.NO_SHOW:
            mark_no_show(booking)
        elif target == BookingStatus.CANCELLED:
            cancel_booking(booking, by_customer=False)
        else:
            raise BookingError("Unsupported status change.")
