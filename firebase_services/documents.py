"""Store user-owned entrant and layout JSON documents in Cloud Firestore."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
import json
import re
from typing import Any

from firebase_admin import firestore

from .client import FirebaseServiceError, firestore_client


DOCUMENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
RESOURCE_COLLECTIONS = frozenset({"entrants", "layouts"})
MAX_DOCUMENT_JSON_BYTES = 900_000
MAX_DOCUMENT_NAME_LENGTH = 120


class FirebaseResourceNotFound(LookupError):
    """Raised when a requested user-owned document does not exist."""


def validate_resource_collection(collection: str) -> str:
    if collection not in RESOURCE_COLLECTIONS:
        raise ValueError("Unknown Firebase document collection")
    return collection


def validate_document_id(document_id: str) -> str:
    if not DOCUMENT_ID.fullmatch(document_id):
        raise ValueError(
            "Document ID must contain 1-128 letters, numbers, underscores, or hyphens"
        )
    return document_id


def validate_saved_document(payload: Any) -> tuple[str, Any]:
    """Validate the API envelope and keep its data Firestore/JSON compatible."""
    if not isinstance(payload, Mapping):
        raise ValueError("Request body must be a JSON object")
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    name = name.strip()
    if len(name) > MAX_DOCUMENT_NAME_LENGTH:
        raise ValueError(f"name must be at most {MAX_DOCUMENT_NAME_LENGTH} characters")
    if "data" not in payload:
        raise ValueError("data is required")
    data = payload["data"]
    if not isinstance(data, Mapping):
        raise ValueError("data must be a JSON object")
    try:
        serialized = json.dumps(data, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ValueError("data must be valid JSON") from error
    if len(serialized.encode("utf-8")) > MAX_DOCUMENT_JSON_BYTES:
        raise ValueError(
            f"data exceeds the {MAX_DOCUMENT_JSON_BYTES}-byte saved-document limit"
        )
    return name, data


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _snapshot_json(snapshot: Any) -> dict[str, Any]:
    result = _json_value(snapshot.to_dict() or {})
    result["id"] = snapshot.id
    return result


class UserDocumentRepository:
    """CRUD repository scoped to ``users/{uid}/{collection}``."""

    def __init__(self, uid: str, collection: str, client: Any | None = None) -> None:
        self._uid = uid
        self._collection_name = validate_resource_collection(collection)
        self._client = client or firestore_client()

    @property
    def collection(self) -> Any:
        return (
            self._client.collection("users")
            .document(self._uid)
            .collection(self._collection_name)
        )

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            query = self.collection.order_by(
                "updatedAt", direction=firestore.Query.DESCENDING
            ).limit(limit)
            return [_snapshot_json(snapshot) for snapshot in query.stream()]
        except Exception as error:
            raise FirebaseServiceError("Could not list saved Firebase documents") from error

    def get(self, document_id: str) -> dict[str, Any]:
        validate_document_id(document_id)
        try:
            snapshot = self.collection.document(document_id).get()
        except Exception as error:
            raise FirebaseServiceError("Could not load the saved Firebase document") from error
        if not snapshot.exists:
            raise FirebaseResourceNotFound(document_id)
        return _snapshot_json(snapshot)

    def create(self, name: str, data: Any) -> dict[str, Any]:
        try:
            reference = self.collection.document()
            reference.set(
                {
                    "schemaVersion": 1,
                    "name": name,
                    "data": data,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            return _snapshot_json(reference.get())
        except Exception as error:
            raise FirebaseServiceError("Could not save the Firebase document") from error

    def replace(self, document_id: str, name: str, data: Any) -> dict[str, Any]:
        validate_document_id(document_id)
        reference = self.collection.document(document_id)
        try:
            if not reference.get().exists:
                raise FirebaseResourceNotFound(document_id)
            reference.set(
                {
                    "schemaVersion": 1,
                    "name": name,
                    "data": data,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            return _snapshot_json(reference.get())
        except FirebaseResourceNotFound:
            raise
        except Exception as error:
            raise FirebaseServiceError("Could not update the Firebase document") from error

    def delete(self, document_id: str) -> None:
        validate_document_id(document_id)
        reference = self.collection.document(document_id)
        try:
            if not reference.get().exists:
                raise FirebaseResourceNotFound(document_id)
            reference.delete()
        except FirebaseResourceNotFound:
            raise
        except Exception as error:
            raise FirebaseServiceError("Could not delete the Firebase document") from error
