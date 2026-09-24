"""Initialize and provide the server-side Firebase Admin clients."""

from __future__ import annotations

import os
from typing import Any

import firebase_admin
from firebase_admin import firestore, storage


FIREBASE_APP_NAME = "melee-podium"


class FirebaseConfigurationError(RuntimeError):
    """Raised when a Firebase service is used without required configuration."""


class FirebaseServiceError(RuntimeError):
    """Raised when a configured Firebase service cannot complete an operation."""


def _environment_value(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def firebase_credentials_are_configured() -> bool:
    """Return whether Application Default Credentials have an available source."""
    return bool(
        _environment_value("GOOGLE_APPLICATION_CREDENTIALS")
        or _environment_value("FIREBASE_CONFIG")
        or _environment_value("GOOGLE_CLOUD_PROJECT")
        or _environment_value("GCLOUD_PROJECT")
    )


def storage_bucket_name() -> str | None:
    """Return a normalized Firebase Storage bucket name, when configured."""
    bucket = _environment_value("FIREBASE_STORAGE_BUCKET")
    if bucket and bucket.startswith("gs://"):
        bucket = bucket[5:]
    return bucket.rstrip("/") if bucket else None


def _existing_app() -> Any | None:
    try:
        return firebase_admin.get_app(FIREBASE_APP_NAME)
    except ValueError:
        return None


def initialize_firebase_if_configured() -> bool:
    """Initialize Firebase Admin once when server credentials are configured.

    Application Default Credentials intentionally read the path from
    GOOGLE_APPLICATION_CREDENTIALS. The credential JSON itself never belongs in
    source code or Flask configuration.
    """
    if _existing_app() is not None:
        return True
    if not firebase_credentials_are_configured():
        return False

    options: dict[str, str] = {}
    bucket = storage_bucket_name()
    if bucket:
        options["storageBucket"] = bucket
    firebase_admin.initialize_app(options=options, name=FIREBASE_APP_NAME)
    return True


def firebase_app() -> Any:
    """Return the initialized Firebase app or explain how to configure it."""
    app = _existing_app()
    if app is not None:
        return app
    if initialize_firebase_if_configured():
        app = _existing_app()
        if app is not None:
            return app
    raise FirebaseConfigurationError(
        "Firebase is not configured on this server. Set "
        "GOOGLE_APPLICATION_CREDENTIALS to the service-account JSON path."
    )


def firestore_client() -> Any:
    """Return an authenticated Cloud Firestore client."""
    return firestore.client(app=firebase_app())


def storage_bucket() -> Any:
    """Return the configured private Cloud Storage bucket."""
    if not storage_bucket_name():
        raise FirebaseConfigurationError(
            "Cloud Storage is not configured. Set FIREBASE_STORAGE_BUCKET to "
            "the bucket name shown in the Firebase console."
        )
    return storage.bucket(app=firebase_app())


def configuration_summary() -> dict[str, bool]:
    """Return non-secret configuration state for diagnostics."""
    return {
        "credentials_configured": firebase_credentials_are_configured(),
        "storage_bucket_configured": storage_bucket_name() is not None,
        "initialized": _existing_app() is not None,
    }
