"""Download short-lived artifacts through server-owned metadata."""

from flask import Blueprint, send_file

from ..errors import ApiError
from ..services.artifacts import (
    ArtifactExpired,
    ArtifactNotFound,
    get_artifact_store,
)


bp = Blueprint("downloads", __name__)


@bp.get("/api/v1/jobs/<job_id>/artifacts/<artifact_id>")
def download_artifact(job_id, artifact_id):
    try:
        artifact = get_artifact_store().resolve_artifact(job_id, artifact_id)
    except ArtifactExpired:
        raise ApiError(
            "ARTIFACT_EXPIRED", "这个处理结果已经过期，请重新处理文件", 410
        ) from None
    except ArtifactNotFound:
        raise ApiError("ARTIFACT_NOT_FOUND", "没有找到这个处理结果", 404) from None

    response = send_file(
        artifact.path,
        mimetype=artifact.content_type,
        as_attachment=True,
        download_name=artifact.name,
        conditional=False,
        max_age=0,
    )
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response
