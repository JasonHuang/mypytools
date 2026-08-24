"""Public site routes."""

from flask import Blueprint, current_app, render_template

from ..tools.registry import get_available_tools


bp = Blueprint("site", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        title="Toolmist — 轻量在线工具箱",
        tools=get_available_tools(),
        site_limits={
            "max_upload_mb": current_app.config["MAX_UPLOAD_MB"],
            "max_files": current_app.config["MAX_FILES_PER_JOB"],
            "retention_hours": current_app.config["FILE_RETENTION_HOURS"],
        },
    )
