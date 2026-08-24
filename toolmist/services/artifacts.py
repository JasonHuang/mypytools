"""Job-scoped storage for short-lived uploaded and generated files."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import re
import secrets
import shutil
import threading

import click
from flask import current_app


JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,40}$")
ARTIFACT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{12,40}$")
METADATA_NAME = "metadata.json"


class ArtifactNotFound(Exception):
    pass


class ArtifactExpired(Exception):
    pass


@dataclass(frozen=True)
class Job:
    id: str
    directory: Path
    created_at: datetime
    expires_at: datetime

    @property
    def inputs(self):
        return self.directory / "inputs"

    @property
    def outputs(self):
        return self.directory / "outputs"


@dataclass(frozen=True)
class Artifact:
    id: str
    name: str
    size: int
    content_type: str
    path: Path


def utc_now():
    return datetime.now(timezone.utc)


def isoformat(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed


class ArtifactStore:
    """Create, resolve, and expire isolated processing jobs."""

    def __init__(self, root, retention_hours):
        self.root = Path(root).resolve()
        self.retention_hours = retention_hours
        self.root.mkdir(parents=True, exist_ok=True)

    def create_job(self):
        created_at = utc_now()
        expires_at = created_at + timedelta(hours=self.retention_hours)
        for _attempt in range(5):
            job_id = secrets.token_urlsafe(18)
            directory = self.root / job_id
            try:
                directory.mkdir(mode=0o700)
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Unable to allocate a processing job")

        job = Job(job_id, directory, created_at, expires_at)
        try:
            job.inputs.mkdir(mode=0o700)
            job.outputs.mkdir(mode=0o700)
            self._write_metadata(job, {
                "version": 1,
                "id": job.id,
                "created_at": isoformat(job.created_at),
                "expires_at": isoformat(job.expires_at),
                "artifacts": {},
            })
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return job

    def input_path(self, job, index, suffix):
        return job.inputs / f"input-{index:03d}{suffix.lower()}"

    def output_path(self, job, index, suffix):
        return job.outputs / f"output-{index:03d}{suffix.lower()}"

    def add_artifact(self, job, path, download_name, content_type):
        path = Path(path).resolve()
        if path.parent != job.outputs.resolve() or not path.is_file():
            raise RuntimeError("Artifact must be a generated job output")

        artifact_id = secrets.token_urlsafe(12)
        metadata = self._read_metadata(job.directory)
        metadata["artifacts"][artifact_id] = {
            "stored_name": path.name,
            "name": download_name,
            "size": path.stat().st_size,
            "content_type": content_type,
        }
        self._write_metadata(job, metadata)
        return Artifact(
            artifact_id,
            download_name,
            path.stat().st_size,
            content_type,
            path,
        )

    def resolve_artifact(self, job_id, artifact_id):
        if not JOB_ID_PATTERN.fullmatch(job_id or ""):
            raise ArtifactNotFound
        if not ARTIFACT_ID_PATTERN.fullmatch(artifact_id or ""):
            raise ArtifactNotFound

        directory = self.root / job_id
        if directory.is_symlink() or not directory.is_dir():
            raise ArtifactNotFound
        try:
            metadata = self._read_metadata(directory)
            expires_at = parse_timestamp(metadata["expires_at"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError, OSError):
            raise ArtifactNotFound from None

        if utc_now() >= expires_at:
            shutil.rmtree(directory, ignore_errors=True)
            raise ArtifactExpired

        record = metadata.get("artifacts", {}).get(artifact_id)
        if not record:
            raise ArtifactNotFound
        stored_name = record.get("stored_name", "")
        if Path(stored_name).name != stored_name:
            raise ArtifactNotFound

        path = (directory / "outputs" / stored_name).resolve()
        if path.parent != (directory / "outputs").resolve() or not path.is_file():
            raise ArtifactNotFound
        try:
            return Artifact(
                artifact_id,
                str(record["name"]),
                int(record["size"]),
                str(record["content_type"]),
                path,
            )
        except (KeyError, TypeError, ValueError):
            raise ArtifactNotFound from None

    def delete_job(self, job):
        shutil.rmtree(job.directory, ignore_errors=True)

    def cleanup_expired(self, now=None):
        now = now or utc_now()
        removed_jobs = 0
        removed_bytes = 0
        fallback_cutoff = now - timedelta(hours=self.retention_hours)
        lock_path = self.root / ".artifact-cleanup.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 0, 0
            try:
                for directory in self.root.iterdir():
                    if directory.is_symlink() or not directory.is_dir():
                        continue
                    if not JOB_ID_PATTERN.fullmatch(directory.name):
                        continue
                    try:
                        metadata = self._read_metadata(directory)
                        expired = now >= parse_timestamp(metadata["expires_at"])
                    except (
                        KeyError,
                        ValueError,
                        TypeError,
                        json.JSONDecodeError,
                        OSError,
                    ):
                        try:
                            expired = datetime.fromtimestamp(
                                directory.stat().st_mtime, timezone.utc
                            ) <= fallback_cutoff
                        except OSError:
                            continue
                    if not expired:
                        continue
                    try:
                        removed_bytes += sum(
                            item.stat().st_size
                            for item in directory.rglob("*")
                            if item.is_file() and not item.is_symlink()
                        )
                    except OSError:
                        pass
                    shutil.rmtree(directory, ignore_errors=True)
                    removed_jobs += 1
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return removed_jobs, removed_bytes

    def _read_metadata(self, directory):
        return json.loads((directory / METADATA_NAME).read_text(encoding="utf-8"))

    def _write_metadata(self, job, metadata):
        temporary = job.directory / ".metadata.tmp"
        temporary.write_text(
            json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(job.directory / METADATA_NAME)


def get_artifact_store():
    return current_app.extensions["toolmist_artifacts"]


def register_artifact_maintenance(app):
    @app.cli.command("cleanup-artifacts")
    def cleanup_artifacts_command():
        """Delete expired Toolmist processing jobs."""
        removed_jobs, removed_bytes = get_artifact_store().cleanup_expired()
        click.echo(f"removed_jobs={removed_jobs} removed_bytes={removed_bytes}")

    if app.config["TESTING"] or not app.config["ENABLE_ARTIFACT_CLEANUP"]:
        return

    interval = app.config["ARTIFACT_CLEANUP_INTERVAL_SECONDS"]

    stop_event = threading.Event()

    def cleanup_loop():
        while not stop_event.wait(interval):
            with app.app_context():
                try:
                    removed_jobs, removed_bytes = get_artifact_store().cleanup_expired()
                    if removed_jobs:
                        app.logger.info(
                            "artifact_cleanup removed_jobs=%s removed_bytes=%s",
                            removed_jobs,
                            removed_bytes,
                        )
                except OSError as exc:
                    app.logger.warning(
                        "artifact_cleanup_failed error_type=%s", type(exc).__name__
                    )

    threading.Thread(
        target=cleanup_loop,
        name="toolmist-artifact-cleanup",
        daemon=True,
    ).start()
