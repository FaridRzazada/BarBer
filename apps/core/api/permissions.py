"""Reusable DRF permissions. The API never relies on the front-end for authz."""
from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCustomer(BasePermission):
    message = "Only customers can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_customer)


class IsProfessional(BasePermission):
    message = "Only professionals can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_professional)


class IsOwner(BasePermission):
    """Object-level: the object's ``user`` attribute must be the requester."""

    def has_object_permission(self, request, view, obj) -> bool:
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        return owner == request.user


class IsProfessionalOwnerOrReadOnly(BasePermission):
    """Read for anyone; write only for the professional that owns the object."""

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        professional = getattr(obj, "professional", None)
        return bool(professional and professional.user == request.user)
