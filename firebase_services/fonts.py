"""Validate and store private user font assets in Cloud Storage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import PurePath
import re
from typing import Any
from uuid import uuid4

from firebase_admin import firestore
from google.api_core.exceptions import NotFound
from PIL import ImageFont
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .client import FirebaseServiceError, firestore_client, storage_bucket
from .documents import FirebaseResourceNotFound, validate_document_id


MAX_FONT_BYTES = 10 * 1024 * 1024
MAX_FONTS_PER_USER = 10
MAX_FONT_NAME_LENGTH = 80
SIGNED_URL_LIFETIME = timedelta(minutes=15)


def validate_font_name(value: str | None) -> tuple[str, str]:
    name = re.sub(r"\s+", " ", value or "").strip()
    if not name:
        raise ValueError("A font name is required")
    if len(name) > MAX_FONT_NAME_LENGTH:
        raise ValueError(f"Font names must be {MAX_FONT_NAME_LENGTH} characters or fewer")
    return name, name.casefold()


def validate_font_bytes(content: bytes) -> tuple[str, str]:
    if not content:
        raise ValueError("The uploaded font is empty")
    if len(content) > MAX_FONT_BYTES:
        raise ValueError("The uploaded font is too large")
    signature = content[:4]
    if signature in {b"OTTO", b"true"}:
        extension, content_type = "otf", "font/otf"
    elif signature == b"\x00\x01\x00\x00":
        extension, content_type = "ttf", "font/ttf"
    else:
        raise ValueError("Fonts must be valid TTF or OTF files")
    try:
        ImageFont.truetype(BytesIO(content), 16)
    except (OSError, ValueError) as error:
        raise ValueError("The upload is not a valid renderable font") from error
    return extension, content_type


def read_font_upload(upload: FileStorage) -> tuple[bytes, str, str, str]:
    content = upload.stream.read(MAX_FONT_BYTES + 1)
    if len(content) > MAX_FONT_BYTES:
        raise ValueError("The uploaded font is too large")
    extension, content_type = validate_font_bytes(content)
    original_name = secure_filename(PurePath(upload.filename or "").name) or f"font.{extension}"
    return content, extension, content_type, original_name


def _font_json(snapshot: Any) -> dict[str, Any]:
    result = snapshot.to_dict() or {}
    for key in ("createdAt", "updatedAt"):
        value = result.get(key)
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    result["id"] = snapshot.id
    return result


class UserFontService:
    def __init__(self, uid: str, client: Any | None = None, bucket: Any | None = None) -> None:
        self._uid = uid
        self._client = client or firestore_client()
        self._bucket = bucket or storage_bucket()

    @property
    def collection(self) -> Any:
        return self._client.collection("users").document(self._uid).collection("fonts")

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            return [_font_json(item) for item in self.collection.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit).stream()]
        except Exception as error:
            raise FirebaseServiceError("Could not list Firebase fonts") from error

    def get(self, font_id: str) -> dict[str, Any]:
        validate_document_id(font_id)
        try:
            snapshot = self.collection.document(font_id).get()
        except Exception as error:
            raise FirebaseServiceError("Could not load the Firebase font") from error
        if not snapshot.exists:
            raise FirebaseResourceNotFound(font_id)
        return _font_json(snapshot)

    def upload(self, upload: FileStorage, *, name: str | None) -> dict[str, Any]:
        display_name, name_key = validate_font_name(name)
        fonts = self.list(100)
        if len(fonts) >= MAX_FONTS_PER_USER:
            raise ValueError(f"You can save up to {MAX_FONTS_PER_USER} fonts")
        if any(font.get("nameKey") == name_key for font in fonts):
            raise ValueError("You already have a font with that name")
        content, extension, content_type, original_name = read_font_upload(upload)
        font_id = uuid4().hex
        storage_path = f"users/{self._uid}/fonts/{font_id}/original.{extension}"
        blob = self._bucket.blob(storage_path)
        blob.cache_control = "private, max-age=3600"
        blob.metadata = {"ownerUid": self._uid, "fontId": font_id}
        try:
            blob.upload_from_string(content, content_type=content_type, if_generation_match=0)
            reference = self.collection.document(font_id)
            reference.set({"schemaVersion": 1, "name": display_name, "nameKey": name_key, "originalFilename": original_name, "storagePath": storage_path, "contentType": content_type, "sizeBytes": len(content), "createdAt": firestore.SERVER_TIMESTAMP, "updatedAt": firestore.SERVER_TIMESTAMP})
            return _font_json(reference.get())
        except Exception as error:
            try:
                blob.delete()
            except Exception:
                pass
            raise FirebaseServiceError("Could not upload the Firebase font") from error

    def signed_download_url(self, font_id: str) -> tuple[str, datetime]:
        metadata = self.get(font_id)
        expiration = datetime.now(timezone.utc) + SIGNED_URL_LIFETIME
        try:
            url = self._bucket.blob(metadata["storagePath"]).generate_signed_url(version="v4", expiration=SIGNED_URL_LIFETIME, method="GET", response_disposition="inline")
        except Exception as error:
            raise FirebaseServiceError("Could not create a font download URL") from error
        return url, expiration

    def delete(self, font_id: str) -> None:
        metadata = self.get(font_id)
        try:
            self._bucket.blob(metadata["storagePath"]).delete()
        except NotFound:
            pass
        except Exception as error:
            raise FirebaseServiceError("Could not delete the stored Firebase font") from error
        try:
            self.collection.document(font_id).delete()
        except Exception as error:
            raise FirebaseServiceError("Could not delete the Firebase font metadata") from error
