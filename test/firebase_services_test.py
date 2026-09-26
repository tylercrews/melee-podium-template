"""Focused tests for Firebase request and serialization boundaries."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from flask import Flask
from PIL import Image
from werkzeug.datastructures import FileStorage

from firebase_services.authentication import bearer_token
from firebase_services.documents import (
    MAX_DOCUMENT_JSON_BYTES,
    validate_document_id,
    validate_saved_document,
)
from firebase_services.images import (
    DEFAULT_MAX_IMAGE_BYTES,
    IMAGE_FORMATS,
    read_image_upload,
    validate_image_bytes,
    validate_image_category,
    validate_image_name,
)
from firebase_services.fonts import MAX_FONT_BYTES, read_font_upload, validate_font_bytes, validate_font_name
from firebase_services.routes import firebase_blueprint


def png_bytes(width: int = 4, height: int = 3) -> bytes:
    output = BytesIO()
    Image.new("RGBA", (width, height), "#12345678").save(output, "PNG")
    return output.getvalue()


def gif_bytes(width: int = 4, height: int = 3) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), "#123456").save(output, "GIF")
    return output.getvalue()


class FirebaseAuthenticationBoundaryTests(unittest.TestCase):
    def test_extracts_bearer_token_case_insensitively(self) -> None:
        self.assertEqual(bearer_token("bearer token-value"), "token-value")

    def test_rejects_missing_or_wrong_authorization_scheme(self) -> None:
        for value in (None, "", "Basic token-value", "Bearer"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bearer_token(value)


class FirebaseDocumentBoundaryTests(unittest.TestCase):
    def test_accepts_named_json_payload(self) -> None:
        name, data = validate_saved_document(
            {"name": " Weekly layout ", "data": {"background": "#00000000"}}
        )
        self.assertEqual(name, "Weekly layout")
        self.assertEqual(data, {"background": "#00000000"})

    def test_rejects_non_json_and_oversized_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            validate_saved_document({"name": "Bad", "data": {"value": object()}})
        with self.assertRaisesRegex(ValueError, "saved-document limit"):
            validate_saved_document(
                {
                    "name": "Large",
                    "data": {"value": "x" * (MAX_DOCUMENT_JSON_BYTES + 1)},
                }
            )

    def test_document_ids_are_restricted_to_safe_path_segments(self) -> None:
        self.assertEqual(validate_document_id("layout_01-test"), "layout_01-test")
        for value in ("", "../other-user", "contains/slash", "contains space"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_document_id(value)


class FirebaseImageBoundaryTests(unittest.TestCase):
    def test_default_upload_limit_is_300_mebibytes(self) -> None:
        self.assertEqual(DEFAULT_MAX_IMAGE_BYTES, 300 * 1024 * 1024)

    def test_normalizes_image_names_and_restricts_categories(self) -> None:
        self.assertEqual(validate_image_name("  Main   Logo  "), ("Main Logo", "main logo"))
        self.assertEqual(validate_image_category("BACKGROUND"), "background")
        for value in (None, "", "other"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_image_category(value)

    def test_detects_image_content_instead_of_trusting_filename(self) -> None:
        upload = FileStorage(
            stream=BytesIO(png_bytes(12, 8)),
            filename="../../unsafe-name.jpg",
            content_type="image/jpeg",
        )
        content, extension, content_type, width, height, filename = read_image_upload(upload)
        self.assertTrue(content.startswith(b"\x89PNG"))
        self.assertEqual((extension, content_type), ("png", "image/png"))
        self.assertEqual((width, height), (12, 8))
        self.assertEqual(filename, "unsafe-name.jpg")

    def test_accepts_gif_content(self) -> None:
        self.assertEqual(validate_image_bytes(gif_bytes(12, 8)), ("gif", "image/gif", 12, 8))

    def test_treats_mpo_as_jpeg_compatible(self) -> None:
        self.assertEqual(IMAGE_FORMATS["MPO"], ("jpg", "image/jpeg"))

    def test_rejects_invalid_and_oversized_image_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid image"):
            validate_image_bytes(b"not an image")
        with patch.dict(os.environ, {"FIREBASE_MAX_IMAGE_BYTES": "4"}):
            with self.assertRaisesRegex(ValueError, "too large"):
                validate_image_bytes(png_bytes())


class FirebaseFontBoundaryTests(unittest.TestCase):
    def test_validates_real_font_bytes_instead_of_the_filename(self) -> None:
        font_bytes = (Path(__file__).resolve().parents[1] / "fonts" / "Ubuntu-Regular.ttf").read_bytes()
        upload = FileStorage(stream=BytesIO(font_bytes), filename="../../unsafe.otf", content_type="font/otf")
        content, extension, content_type, filename = read_font_upload(upload)
        self.assertEqual(content, font_bytes)
        self.assertEqual((extension, content_type, filename), ("ttf", "font/ttf", "unsafe.otf"))

    def test_rejects_invalid_fonts_and_normalizes_names(self) -> None:
        self.assertEqual(validate_font_name("  Event   Sans  "), ("Event Sans", "event sans"))
        self.assertEqual(MAX_FONT_BYTES, 10 * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, "TTF or OTF"):
            validate_font_bytes(b"not a font")


class FirebaseRouteTests(unittest.TestCase):
    def test_static_image_routes_win_over_generic_document_routes(self) -> None:
        app = Flask(__name__)
        app.register_blueprint(firebase_blueprint)
        adapter = app.url_map.bind("example.test")
        endpoint, _values = adapter.match("/api/firebase/images", method="GET")
        self.assertEqual(endpoint, "firebase.list_images")
        endpoint, _values = adapter.match(
            "/api/firebase/images/image-id", method="GET"
        )
        self.assertEqual(endpoint, "firebase.get_image")
        endpoint, _values = adapter.match("/api/firebase/fonts", method="GET")
        self.assertEqual(endpoint, "firebase.list_fonts")


if __name__ == "__main__":
    unittest.main()
