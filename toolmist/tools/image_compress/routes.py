"""Image compression API v1."""

import math

from flask import Blueprint, current_app, request, url_for

from ...errors import ApiError
from ...services.artifacts import get_artifact_store, isoformat
from ...services.images import (
    compress_to_jpeg,
    image_stem,
    save_and_validate_upload,
    upload_extension,
)
from ...services.limits import guard_processing_job


bp = Blueprint("image_compress", __name__)


def artifact_payload(job, artifact):
    return {
        "id": artifact.id,
        "name": artifact.name,
        "size": artifact.size,
        "content_type": artifact.content_type,
        "download_url": url_for(
            "downloads.download_artifact",
            job_id=job.id,
            artifact_id=artifact.id,
        ),
    }


@bp.post("/api/v1/tools/image-compress/jobs")
@guard_processing_job
def create_compression_job():
    if request.mimetype != "multipart/form-data":
        raise ApiError("UPLOAD_REQUIRED", "请通过文件上传方式提交图片")

    upload = request.files.get("file")
    if not upload or not upload.filename:
        raise ApiError("FILE_REQUIRED", "请选择一张需要压缩的图片")
    extension = upload_extension(upload.filename)
    try:
        target_size_mb = float(request.form.get("target_size_mb", "2"))
    except (TypeError, ValueError):
        raise ApiError("INVALID_TARGET_SIZE", "目标大小格式不正确") from None
    if not math.isfinite(target_size_mb) or not 0.1 <= target_size_mb <= 50:
        raise ApiError(
            "INVALID_TARGET_SIZE", "目标大小必须在 0.1 MB 到 50 MB 之间"
        )

    store = get_artifact_store()
    job = None
    try:
        store.cleanup_expired()
        job = store.create_job()
        input_path = store.input_path(job, 1, extension)
        source = save_and_validate_upload(
            upload,
            input_path,
            current_app.config["MAX_IMAGE_PIXELS"],
        )
        output_path = store.output_path(job, 1, ".jpg")
        compress_to_jpeg(source.path, output_path, target_size_mb)
        output_name = f"{image_stem(source.original_name)}-compressed.jpg"
        artifact = store.add_artifact(
            job, output_path, output_name, "image/jpeg"
        )
        source.path.unlink(missing_ok=True)
    except ApiError:
        if job:
            store.delete_job(job)
        raise
    except Exception as exc:
        if job:
            store.delete_job(job)
        current_app.logger.error(
            "image_compress_failed error_type=%s", type(exc).__name__
        )
        raise ApiError(
            "PROCESSING_FAILED", "图片压缩失败，请稍后重试", 422
        ) from None

    current_app.logger.info(
        "tool_job tool=image-compress status=success input_count=1 input_bytes=%s pixels=%s",
        source.size,
        source.pixels,
    )
    return {
        "ok": True,
        "job": {"id": job.id, "expires_at": isoformat(job.expires_at)},
        "artifacts": [artifact_payload(job, artifact)],
        "summary": {
            "input_size": source.size,
            "output_size": artifact.size,
            "target_size_mb": target_size_mb,
        },
    }, 201
