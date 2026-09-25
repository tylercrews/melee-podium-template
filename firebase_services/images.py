"""Validate and store private user images in Cloud Storage for Firebase."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
from pathlib import PurePath
import re
from typing import Any
from uuid import uuid4

from firebase_admin import firestore
from google.api_core.exceptions import NotFound
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .client import FirebaseServiceError, firestore_client, storage_bucket
from .documents import FirebaseResourceNotFound, validate_document_id


DEFAULT_MAX_IMAGE_BYTES = 300 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
SIGNED_URL_LIFETIME = timedelta(minutes=15)
MAX_IMAGES_PER_CATEGORY = 10
MAX_IMAGE_NAME_LENGTH = 80
IMAGE_CATEGORIES = frozenset({"tournament_logo", "background"})
IMAGE_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "MPO": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
    "GIF": ("gif", "image/gif"),
    "BMP": ("bmp", "image/bmp"),
}


def validate_image_name(value: str | None) -> tuple[str, str]:
    """Return a display name and case-insensitive key for a saved image."""
    name = re.sub(r"\s+", " ", value or "").strip()
    if not name:
        raise ValueError("An image name is required")
    if len(name) > MAX_IMAGE_NAME_LENGTH:
        raise ValueError(f"Image names must be {MAX_IMAGE_NAME_LENGTH} characters or fewer")
    return name, name.casefold()


def validate_image_category(value: str | None) -> str:
    category = (value or "").strip().lower()
    if category not in IMAGE_CATEGORIES:
        raise ValueError("Image category must be tournament_logo or background")
    return category


def maximum_image_bytes() -> int:
    raw_value = os.environ.get("FIREBASE_MAX_IMAGE_BYTES", str(DEFAULT_MAX_IMAGE_BYTES))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError("FIREBASE_MAX_IMAGE_BYTES must be an integer") from error
    if value < 1:
        raise ValueError("FIREBASE_MAX_IMAGE_BYTES must be positive")
    return value


def validate_image_bytes(content: bytes) -> tuple[str, str, int, int]:
    """Return extension, MIME type, width, and height for an allowed raster image."""
    if not content:
        raise ValueError("The uploaded image is empty")
    if len(content) > maximum_image_bytes():
        raise ValueError("The uploaded image is too large")
    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ValueError("The upload is not a valid image") from error
    if image_format not in IMAGE_FORMATS:
        detected = image_format or "unknown"
        raise ValueError(
            "Images must be PNG, JPG/JPEG, WebP, GIF, or BMP "
            f"(detected {detected})"
        )
    if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
        raise ValueError(
            f"Images must contain between 1 and {MAX_IMAGE_PIXELS:,} pixels"
        )
    extension, content_type = IMAGE_FORMATS[image_format]
    return extension, content_type, width, height


def read_image_upload(upload: FileStorage) -> tuple[bytes, str, str, int, int, str]:
    """Read one bounded upload and return validated storage metadata."""
    maximum = maximum_image_bytes()
    content = upload.stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("The uploaded image is too large")
    extension, content_type, width, height = validate_image_bytes(content)
    original_name = secure_filename(PurePath(upload.filename or "").name)
    if not original_name:
        original_name = f"image.{extension}"
    return content, extension, content_type, width, height, original_name


def _image_json(snapshot: Any) -> dict[str, Any]:
    result = snapshot.to_dict() or {}
    for key in ("createdAt", "updatedAt"):
        value = result.get(key)
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    result["id"] = snapshot.id
    return result


class UserImageService:
    """Manage private images and their Firestore metadata for one verified user."""

    def __init__(self, uid: str, client: Any | None = None, bucket: Any | None = None) -> None:
        self._uid = uid
        self._client = client or firestore_client()
        self._bucket = bucket or storage_bucket()

    @property
    def collection(self) -> Any:
        return self._client.collection("users").document(self._uid).collection("images")

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            query = self.collection.order_by(
                "createdAt", direction=firestore.Query.DESCENDING
            ).limit(limit)
            return [_image_json(snapshot) for snapshot in query.stream()]
        except Exception as error:
            raise FirebaseServiceError("Could not list Firebase images") from error

    def get(self, image_id: str) -> dict[str, Any]:
        validate_document_id(image_id)
        try:
            snapshot = self.collection.document(image_id).get()
        except Exception as error:
            raise FirebaseServiceError("Could not load the Firebase image") from error
        if not snapshot.exists:
            raise FirebaseResourceNotFound(image_id)
        return _image_json(snapshot)

    def upload(
        self,
        upload: FileStorage,
        *,
        name: str | None,
        category: str | None,
    ) -> dict[str, Any]:
        display_name, name_key = validate_image_name(name)
        image_category = validate_image_category(category)
        category_images = [
            image for image in self.list(100) if image.get("category") == image_category
        ]
        if len(category_images) >= MAX_IMAGES_PER_CATEGORY:
            label = "tournament logos" if image_category == "tournament_logo" else "backgrounds"
            raise ValueError(f"You can save up to {MAX_IMAGES_PER_CATEGORY} {label}")
        if any(image.get("nameKey") == name_key for image in category_images):
            raise ValueError("You already have an image with that name in this category")

        content, extension, content_type, width, height, original_name = read_image_upload(upload)
        image_id = uuid4().hex
        storage_path = f"users/{self._uid}/images/{image_id}/original.{extension}"
        blob = self._bucket.blob(storage_path)
        blob.cache_control = "private, max-age=3600"
        blob.metadata = {"ownerUid": self._uid, "imageId": image_id}
        try:
            blob.upload_from_string(
                content,
                content_type=content_type,
                if_generation_match=0,
            )
            reference = self.collection.document(image_id)
            reference.set(
                {
                    "schemaVersion": 1,
                    "name": display_name,
                    "nameKey": name_key,
                    "category": image_category,
                    "originalFilename": original_name,
                    "storagePath": storage_path,
                    "contentType": content_type,
                    "sizeBytes": len(content),
                    "width": width,
                    "height": height,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            return _image_json(reference.get())
        except Exception as error:
            try:
                blob.delete()
            except Exception:
                pass
            raise FirebaseServiceError("Could not upload the Firebase image") from error

    def signed_download_url(self, image_id: str) -> tuple[str, datetime]:
        metadata = self.get(image_id)
        expiration = datetime.now(timezone.utc) + SIGNED_URL_LIFETIME
        try:
            url = self._bucket.blob(metadata["storagePath"]).generate_signed_url(
                version="v4",
                expiration=SIGNED_URL_LIFETIME,
                method="GET",
                response_disposition="inline",
            )
        except Exception as error:
            raise FirebaseServiceError("Could not create an image download URL") from error
        return url, expiration

    def delete(self, image_id: str) -> None:
        metadata = self.get(image_id)
        try:
            self._bucket.blob(metadata["storagePath"]).delete()
        except NotFound:
            pass
        except Exception as error:
            raise FirebaseServiceError("Could not delete the stored Firebase image") from error
        try:
            self.collection.document(image_id).delete()
        except Exception as error:
            raise FirebaseServiceError("Could not delete the Firebase image metadata") from error
