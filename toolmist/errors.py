"""Application-wide error handlers."""

from flask import current_app, jsonify
from werkzeug.exceptions import RequestEntityTooLarge


def register_error_handlers(app):
    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        max_upload_mb = current_app.config["MAX_UPLOAD_MB"]
        return jsonify({
            "success": False,
            "error": f"上传内容不能超过 {max_upload_mb} MB",
        }), 413
