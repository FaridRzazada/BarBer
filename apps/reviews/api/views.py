from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.professionals.models import ProfessionalProfile

from ..models import Review
from ..services import ReviewError, create_review
from .serializers import ReviewCreateSerializer, ReviewSerializer


class ReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        professional_id = request.query_params.get("professional")
        professional = get_object_or_404(ProfessionalProfile, pk=professional_id)
        qs = Review.objects.filter(professional=professional).select_related(
            "customer", "booking__service"
        )
        data = ReviewSerializer(qs, many=True).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = get_object_or_404(Booking, pk=serializer.validated_data["booking"])
        try:
            review = create_review(
                customer=request.user,
                booking=booking,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
        except ReviewError as exc:
            return Response(
                {"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {"success": True, "review": ReviewSerializer(review).data},
            status=status.HTTP_201_CREATED,
        )
