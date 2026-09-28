from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.professionals.models import Favorite, ProfessionalProfile


class FavoriteToggleView(APIView):
    """POST {professional: id} → toggles the favorite, returns its new state."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        professional = get_object_or_404(
            ProfessionalProfile, pk=request.data.get("professional")
        )
        favorite = Favorite.objects.filter(
            user=request.user, professional=professional
        ).first()
        if favorite:
            favorite.delete()
            favorited = False
        else:
            Favorite.objects.create(user=request.user, professional=professional)
            favorited = True
        count = professional.favorited_by.count()
        return Response({"success": True, "favorited": favorited, "count": count})


class FavoriteDestroyView(APIView):
    """DELETE /api/favorites/<professional_id>/ — remove a favorite."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, professional_id: int):
        Favorite.objects.filter(
            user=request.user, professional_id=professional_id
        ).delete()
        return Response({"success": True, "favorited": False})
