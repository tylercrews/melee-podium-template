"""Dedicated, local logging for Firebase operation failures."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


FIREBASE_LOGGER_NAME = "melee_podium.firebase"


def configure_firebase_error_logging(project_root: Path) -> Path:
    """Write Firebase tracebacks to a small rotating application-local log."""
    configured_path = os.environ.get("FIREBASE_ERROR_LOG", "").strip()
    log_path = Path(configured_path) if configured_path else project_root / "firebase-errors.log"
    log_path = log_path.expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(FIREBASE_LOGGER_NAME)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    target = str(log_path)
    if not any(
        isinstance(handler, RotatingFileHandler)
        and str(Path(handler.baseFilename).resolve()) == target
        for handler in logger.handlers
    ):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
            delay=True,
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)

    return log_path


def firebase_error_logger() -> logging.Logger:
    """Return the logger reserved for server-side Firebase failures."""
    return logging.getLogger(FIREBASE_LOGGER_NAME)
