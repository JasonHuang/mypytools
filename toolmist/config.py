"""Environment-backed Toolmist configuration."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read_int(name, default, minimum=0):
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


def _read_bool(name, default):
    raw_value = os.getenv(name, "true" if default else "false").strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean")


def _normalize_bool(name, value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean")


class Config:
    MAX_UPLOAD_MB = _read_int("MAX_UPLOAD_MB", 50, minimum=1)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    MAX_FILES_PER_JOB = _read_int("MAX_FILES_PER_JOB", 10, minimum=1)
    MAX_IMAGE_PIXELS = _read_int("MAX_IMAGE_PIXELS", 40_000_000, minimum=1)
    MAX_TOTAL_PIXELS = _read_int("MAX_TOTAL_PIXELS", 100_000_000, minimum=1)
    FILE_RETENTION_HOURS = _read_int("FILE_RETENTION_HOURS", 1)
    ARTIFACT_CLEANUP_INTERVAL_SECONDS = _read_int(
        "ARTIFACT_CLEANUP_INTERVAL_SECONDS", 600, minimum=1
    )
    ENABLE_ARTIFACT_CLEANUP = _read_bool("ENABLE_ARTIFACT_CLEANUP", True)
    UPLOAD_FOLDER = Path(
        os.getenv("UPLOAD_FOLDER", str(PROJECT_ROOT / "uploads"))
    ).resolve()


def apply_runtime_config(config, overrides):
    """Normalize and validate values after test or runtime overrides."""
    try:
        max_upload_mb = int(config["MAX_UPLOAD_MB"])
        max_files = int(config["MAX_FILES_PER_JOB"])
        max_image_pixels = int(config["MAX_IMAGE_PIXELS"])
        max_total_pixels = int(config["MAX_TOTAL_PIXELS"])
        retention_hours = int(config["FILE_RETENTION_HOURS"])
        cleanup_interval = int(config["ARTIFACT_CLEANUP_INTERVAL_SECONDS"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Toolmist numeric configuration is invalid") from exc

    if max_upload_mb < 1:
        raise RuntimeError("MAX_UPLOAD_MB must be at least 1")
    if max_files < 1:
        raise RuntimeError("MAX_FILES_PER_JOB must be at least 1")
    if max_image_pixels < 1:
        raise RuntimeError("MAX_IMAGE_PIXELS must be at least 1")
    if max_total_pixels < max_image_pixels:
        raise RuntimeError("MAX_TOTAL_PIXELS cannot be smaller than MAX_IMAGE_PIXELS")
    if retention_hours < 0:
        raise RuntimeError("FILE_RETENTION_HOURS cannot be negative")
    if cleanup_interval < 1:
        raise RuntimeError("ARTIFACT_CLEANUP_INTERVAL_SECONDS must be at least 1")

    config["MAX_UPLOAD_MB"] = max_upload_mb
    config["MAX_FILES_PER_JOB"] = max_files
    config["MAX_IMAGE_PIXELS"] = max_image_pixels
    config["MAX_TOTAL_PIXELS"] = max_total_pixels
    config["FILE_RETENTION_HOURS"] = retention_hours
    config["ARTIFACT_CLEANUP_INTERVAL_SECONDS"] = cleanup_interval
    config["ENABLE_ARTIFACT_CLEANUP"] = _normalize_bool(
        "ENABLE_ARTIFACT_CLEANUP", config["ENABLE_ARTIFACT_CLEANUP"]
    )
    if "MAX_CONTENT_LENGTH" not in overrides:
        config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024

    upload_folder = Path(config["UPLOAD_FOLDER"]).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)
    config["UPLOAD_FOLDER"] = upload_folder
