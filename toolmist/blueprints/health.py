"""Container and reverse-proxy health routes."""

from flask import Blueprint, jsonify


bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthcheck():
    return jsonify({"status": "ok"})
