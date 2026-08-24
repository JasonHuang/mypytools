"""HTTP security headers, request identifiers, and concise structured logs."""

import json
import logging
import secrets
import time

from flask import g, request


CONTENT_SECURITY_POLICY = "; ".join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))


def register_http_middleware(app):
    app.logger.setLevel(logging.WARNING if app.config["TESTING"] else logging.INFO)

    @app.before_request
    def start_request():
        g.request_id = secrets.token_hex(8)
        g.request_started_at = time.perf_counter()

    @app.after_request
    def finalize_request(response):
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")

        if request.path != "/healthz" and not request.path.startswith("/static/"):
            duration_ms = round(
                (time.perf_counter() - g.get("request_started_at", time.perf_counter()))
                * 1000,
                2,
            )
            app.logger.info(json.dumps({
                "event": "http_request",
                "request_id": g.get("request_id", ""),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "remote_ip": request.remote_addr or "unknown",
            }, separators=(",", ":")))
        return response
