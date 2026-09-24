"""Authenticate Flask API requests with Firebase Authentication ID tokens."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import wraps
import os
from typing import Any, ParamSpec, TypeVar, cast

from firebase_admin import auth
from flask import Response, current_app, g, jsonify, request

from .client import FirebaseConfigurationError, firebase_app


P = ParamSpec("P")
R = TypeVar("R")


def bearer_token(authorization: str | None) -> str:
    """Extract a token from an RFC 6750-style Authorization header."""
    if not authorization:
        raise ValueError("Missing Authorization header")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise ValueError("Authorization must use 'Bearer <Firebase ID token>'")
    return token.strip()


def _check_revoked_tokens() -> bool:
    return os.environ.get("FIREBASE_CHECK_REVOKED_TOKENS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def verify_request_user() -> Mapping[str, Any]:
    """Verify the current request's Firebase ID token and return its claims."""
    token = bearer_token(request.headers.get("Authorization"))
    decoded = auth.verify_id_token(
        token,
        app=firebase_app(),
        check_revoked=_check_revoked_tokens(),
    )
    uid = decoded.get("uid")
    if not isinstance(uid, str) or not uid:
        raise ValueError("Firebase ID token does not contain a valid uid")
    return cast(Mapping[str, Any], decoded)


def require_firebase_user(function: Callable[P, R]) -> Callable[P, R | tuple[Response, int]]:
    """Require a valid Firebase ID token and expose its claims on Flask ``g``."""
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | tuple[Response, int]:
        try:
            g.firebase_user = verify_request_user()
        except FirebaseConfigurationError as error:
            return jsonify(error=str(error)), 503
        except auth.RevokedIdTokenError:
            return jsonify(error="The Firebase session has been revoked"), 401
        except (ValueError, auth.InvalidIdTokenError):
            return jsonify(error="A valid Firebase ID token is required"), 401
        except auth.UserDisabledError:
            return jsonify(error="This Firebase user is disabled"), 403
        except Exception:
            current_app.logger.exception("Firebase ID-token verification failed")
            return jsonify(error="Authentication service is temporarily unavailable"), 503
        return function(*args, **kwargs)

    return wrapped


def current_user() -> Mapping[str, Any]:
    """Return claims set by :func:`require_firebase_user`."""
    claims = getattr(g, "firebase_user", None)
    if not isinstance(claims, Mapping):
        raise RuntimeError("This endpoint requires Firebase authentication")
    return cast(Mapping[str, Any], claims)


def current_user_id() -> str:
    return cast(str, current_user()["uid"])
