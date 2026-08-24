"""Public site routes."""

from flask import Blueprint, render_template

from ..tools.registry import get_available_tools


bp = Blueprint("site", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        title="图片处理工具",
        tools=get_available_tools(),
    )
