"""Flask routes for authenticated Firebase-backed user resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from .authentication import current_user, current_user_id, require_firebase_user
from .client import (
    FirebaseConfigurationError,
    FirebaseServiceError,
    configuration_summary,
)
from .documents import (
    FirebaseResourceNotFound,
    UserDocumentRepository,
    validate_resource_collection,
    validate_saved_document,
)
from .images import UserImageService, maximum_image_bytes


firebase_blueprint = Blueprint("firebase", __name__, url_prefix="/api/firebase")


def _request_json() -> Mapping[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, Mapping):
        raise ValueError("Request body must be a JSON object")
    return payload


def _limit() -> int:
    raw_value = request.args.get("limit", "100")
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError("limit must be an integer") from error
    if not 1 <= value <= 100:
        raise ValueError("limit must be between 1 and 100")
    return value


def _documents(collection: str) -> UserDocumentRepository:
    return UserDocumentRepository(current_user_id(), validate_resource_collection(collection))


@firebase_blueprint.errorhandler(ValueError)
def invalid_request(error: ValueError) -> tuple[Any, int]:
    return jsonify(error=str(error)), 400


@firebase_blueprint.errorhandler(FirebaseResourceNotFound)
def resource_not_found(_error: FirebaseResourceNotFound) -> tuple[Any, int]:
    return jsonify(error="Firebase resource not found"), 404


@firebase_blueprint.errorhandler(FirebaseConfigurationError)
def firebase_not_configured(error: FirebaseConfigurationError) -> tuple[Any, int]:
    return jsonify(error=str(error)), 503


@firebase_blueprint.errorhandler(FirebaseServiceError)
def firebase_operation_failed(error: FirebaseServiceError) -> tuple[Any, int]:
    current_app.logger.exception("Firebase operation failed", exc_info=error.__cause__ or error)
    return jsonify(error=str(error)), 503


@firebase_blueprint.get("/status")
def status() -> Any:
    return jsonify(configuration_summary())


@firebase_blueprint.get("/me")
@require_firebase_user
def me() -> Any:
    claims = current_user()
    firebase_claims = claims.get("firebase", {})
    provider = firebase_claims.get("sign_in_provider") if isinstance(firebase_claims, Mapping) else None
    return jsonify(
        uid=claims["uid"],
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified")),
        name=claims.get("name"),
        picture=claims.get("picture"),
        sign_in_provider=provider,
    )


@firebase_blueprint.get("/<collection>")
@require_firebase_user
def list_documents(collection: str) -> Any:
    return jsonify(items=_documents(collection).list(_limit()))


@firebase_blueprint.post("/<collection>")
@require_firebase_user
def create_document(collection: str) -> Any:
    name, data = validate_saved_document(_request_json())
    document = _documents(collection).create(name, data)
    return jsonify(document), 201


@firebase_blueprint.get("/<collection>/<document_id>")
@require_firebase_user
def get_document(collection: str, document_id: str) -> Any:
    return jsonify(_documents(collection).get(document_id))


@firebase_blueprint.put("/<collection>/<document_id>")
@require_firebase_user
def replace_document(collection: str, document_id: str) -> Any:
    name, data = validate_saved_document(_request_json())
    return jsonify(_documents(collection).replace(document_id, name, data))


@firebase_blueprint.delete("/<collection>/<document_id>")
@require_firebase_user
def delete_document(collection: str, document_id: str) -> tuple[str, int]:
    _documents(collection).delete(document_id)
    return "", 204


@firebase_blueprint.get("/images")
@require_firebase_user
def list_images() -> Any:
    return jsonify(items=UserImageService(current_user_id()).list(_limit()))


@firebase_blueprint.post("/images")
@require_firebase_user
def upload_image() -> Any:
    content_length = request.content_length
    if content_length is not None and content_length > maximum_image_bytes() + 1_000_000:
        return jsonify(error="The uploaded image is too large"), 413
    upload = request.files.get("file")
    if upload is None:
        raise ValueError("A multipart file field named 'file' is required")
    return jsonify(
        UserImageService(current_user_id()).upload(
            upload,
            name=request.form.get("name"),
            category=request.form.get("category"),
        )
    ), 201


@firebase_blueprint.get("/images/<image_id>")
@require_firebase_user
def get_image(image_id: str) -> Any:
    return jsonify(UserImageService(current_user_id()).get(image_id))


@firebase_blueprint.post("/images/<image_id>/download-url")
@require_firebase_user
def image_download_url(image_id: str) -> Any:
    url, expiration = UserImageService(current_user_id()).signed_download_url(image_id)
    return jsonify(url=url, expires_at=expiration.isoformat())


@firebase_blueprint.delete("/images/<image_id>")
@require_firebase_user
def delete_image(image_id: str) -> tuple[str, int]:
    UserImageService(current_user_id()).delete(image_id)
    return "", 204
