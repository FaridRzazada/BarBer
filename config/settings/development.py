"""Development settings — safe defaults, verbose errors, console email."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

# Emails print to the console during development.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow the browser front-end talking to the API from the dev server.
CORS_ALLOW_ALL_ORIGINS = True

# Make DRF's browsable API available while developing.
REST_FRAMEWORK = {**globals()["REST_FRAMEWORK"]}
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
