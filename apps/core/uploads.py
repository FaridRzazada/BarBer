"""Deterministic, collision-free upload paths for user-supplied media.

Filenames are replaced with a random hex token so we never trust (or leak) the
uploader's original filename, and files are grouped into sensible folders.
"""
from __future__ import annotations

import os
import uuid


def _random_name(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"


def avatar_upload_to(instance, filename: str) -> str:
    return f"avatars/{_random_name(filename)}"


def professional_profile_image_upload_to(instance, filename: str) -> str:
    return f"professionals/profile/{_random_name(filename)}"


def professional_cover_upload_to(instance, filename: str) -> str:
    return f"professionals/cover/{_random_name(filename)}"


def portfolio_upload_to(instance, filename: str) -> str:
    return f"portfolio/{_random_name(filename)}"


def gallery_upload_to(instance, filename: str) -> str:
    return f"gallery/{_random_name(filename)}"


def product_image_upload_to(instance, filename: str) -> str:
    return f"products/{_random_name(filename)}"
