"""Image format conversion API v1."""

import zipfile

from flask import Blueprint, current_app, request, url_for

from ...errors import ApiError
from ...services.artifacts import get_artifact_store, isoformat
from ...services.images import (
    convert_image,
    image_stem,
    save_and_validate_upload,
    upload_extension,
)
from ...services.limits import guard_processing_job


bp = Blueprint("image_convert", __name__)

CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def unique_output_name(source_name, output_format, used_names):
    base = image_stem(source_name)
    candidate = f"{base}.{output_format}"
    suffix = 2
    while candidate.casefold() in used_names:
        candidate = f"{base}-{suffix}.{output_format}"
        suffix += 1
    used_names.add(candidate.casefold())
    return candidate


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


@bp.post("/api/v1/tools/image-convert/jobs")
@guard_processing_job
def create_conversion_job():
    if request.mimetype != "multipart/form-data":
        raise ApiError("UPLOAD_REQUIRED", "请通过文件上传方式提交图片")
    uploads = [item for item in request.files.getlist("files") if item.filename]
    if not uploads:
        raise ApiError("FILES_REQUIRED", "请选择需要转换的图片")
    if len(uploads) > current_app.config["MAX_FILES_PER_JOB"]:
        raise ApiError(
            "TOO_MANY_FILES",
            f"每次最多转换 {current_app.config['MAX_FILES_PER_JOB']} 张图片",
            413,
        )

    output_format = request.form.get("output_format", "jpg").lower()
    if output_format == "jpeg":
        output_format = "jpg"
    if output_format not in CONTENT_TYPES:
        raise ApiError("INVALID_OUTPUT_FORMAT", "目标格式仅支持 JPG、PNG 和 WebP")
    try:
        quality = int(request.form.get("quality", "90"))
    except (TypeError, ValueError):
        raise ApiError("INVALID_QUALITY", "转换质量格式不正确") from None
    if not 1 <= quality <= 100:
        raise ApiError("INVALID_QUALITY", "转换质量必须在 1 到 100 之间")

    extensions = [upload_extension(upload.filename) for upload in uploads]
    store = get_artifact_store()
    job = None
    sources = []
    try:
        store.cleanup_expired()
        job = store.create_job()
        total_pixels = 0
        total_bytes = 0
        for index, (upload, extension) in enumerate(
            zip(uploads, extensions), start=1
        ):
            source = save_and_validate_upload(
                upload,
                store.input_path(job, index, extension),
                current_app.config["MAX_IMAGE_PIXELS"],
            )
            sources.append(source)
            total_pixels += source.pixels
            total_bytes += source.size
            if total_pixels > current_app.config["MAX_TOTAL_PIXELS"]:
                raise ApiError(
                    "TOTAL_PIXELS_EXCEEDED",
                    "本次上传图片的总像素超过允许范围",
                    413,
                )

        used_names = set()
        converted_outputs = []
        for index, source in enumerate(sources, start=1):
            output_path = store.output_path(job, index, f".{output_format}")
            output_name = unique_output_name(
                source.original_name, output_format, used_names
            )
            convert_image(source.path, output_path, output_format, quality)
            converted_outputs.append((output_path, output_name))

        if len(converted_outputs) == 1:
            output_path, output_name = converted_outputs[0]
            artifact = store.add_artifact(
                job,
                output_path,
                output_name,
                CONTENT_TYPES[output_format],
            )
        else:
            archive_path = store.output_path(job, 0, ".zip")
            with zipfile.ZipFile(
                archive_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for output_path, output_name in converted_outputs:
                    archive.write(output_path, arcname=output_name)
            for output_path, _output_name in converted_outputs:
                output_path.unlink(missing_ok=True)
            artifact = store.add_artifact(
                job,
                archive_path,
                "converted-images.zip",
                "application/zip",
            )

        for source in sources:
            source.path.unlink(missing_ok=True)
    except ApiError:
        if job:
            store.delete_job(job)
        raise
    except Exception as exc:
        if job:
            store.delete_job(job)
        current_app.logger.error(
            "image_convert_failed error_type=%s", type(exc).__name__
        )
        raise ApiError(
            "PROCESSING_FAILED", "图片格式转换失败，请稍后重试", 422
        ) from None

    current_app.logger.info(
        "tool_job tool=image-convert status=success input_count=%s input_bytes=%s pixels=%s",
        len(sources),
        total_bytes,
        total_pixels,
    )
    return {
        "ok": True,
        "job": {"id": job.id, "expires_at": isoformat(job.expires_at)},
        "artifacts": [artifact_payload(job, artifact)],
        "summary": {
            "input_count": len(sources),
            "input_size": total_bytes,
            "output_size": artifact.size,
            "output_format": output_format,
        },
    }, 201
