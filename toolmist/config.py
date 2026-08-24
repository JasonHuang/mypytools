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


class Config:
    MAX_UPLOAD_MB = _read_int("MAX_UPLOAD_MB", 50, minimum=1)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    FILE_RETENTION_HOURS = _read_int("FILE_RETENTION_HOURS", 24)
    UPLOAD_FOLDER = Path(
        os.getenv("UPLOAD_FOLDER", str(PROJECT_ROOT / "uploads"))
    ).resolve()


def apply_runtime_config(config, overrides):
    """Normalize and validate values after test or runtime overrides."""
    try:
        max_upload_mb = int(config["MAX_UPLOAD_MB"])
        retention_hours = int(config["FILE_RETENTION_HOURS"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Toolmist numeric configuration is invalid") from exc

    if max_upload_mb < 1:
        raise RuntimeError("MAX_UPLOAD_MB must be at least 1")
    if retention_hours < 0:
        raise RuntimeError("FILE_RETENTION_HOURS cannot be negative")

    config["MAX_UPLOAD_MB"] = max_upload_mb
    config["FILE_RETENTION_HOURS"] = retention_hours
    if "MAX_CONTENT_LENGTH" not in overrides:
        config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024

    upload_folder = Path(config["UPLOAD_FOLDER"]).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)
    config["UPLOAD_FOLDER"] = upload_folder
