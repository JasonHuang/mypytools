"""Stable public API errors and application-wide error handlers."""

from flask import current_app, jsonify
from werkzeug.exceptions import RequestEntityTooLarge


class ApiError(Exception):
    """A user-safe API error with a stable machine-readable code."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(code, message, status):
    return jsonify({
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def api_error(error):
        return error_response(error.code, error.message, error.status)

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        max_upload_mb = current_app.config["MAX_UPLOAD_MB"]
        return error_response(
            "REQUEST_TOO_LARGE",
            f"单次上传内容不能超过 {max_upload_mb} MB",
            413,
        )
