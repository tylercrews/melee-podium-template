"""Firebase-backed authentication, saved data, and image storage services."""

from .client import initialize_firebase_if_configured
from .routes import firebase_blueprint

__all__ = ("firebase_blueprint", "initialize_firebase_if_configured")
