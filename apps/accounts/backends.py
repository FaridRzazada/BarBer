"""Authentication backend allowing login by email (or, as a fallback, username)."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = username or kwargs.get("email")
        if identifier is None or password is None:
            return None
        try:
            user = UserModel.objects.get(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            # Run the default hasher once to reduce timing differences.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(email__iexact=identifier).order_by("id").first()
            if user is None:
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
