"""Consistent API error envelope.

Every failed API response looks like::

    {"success": false, "error": "<human message>", "detail": <original DRF body>}

so the front-end can reliably surface a message (see static/js/api.js).
"""
from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler


def _extract_message(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        # First field error, if any.
        for value in data.values():
            if isinstance(value, (list, tuple)) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
        return "Request could not be completed."
    if isinstance(data, (list, tuple)) and data:
        return str(data[0])
    return str(data)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    response.data = {
        "success": False,
        "error": _extract_message(response.data),
        "detail": response.data,
    }
    return response
