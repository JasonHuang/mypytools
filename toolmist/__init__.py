"""Toolmist Flask application factory."""

from pathlib import Path

from flask import Flask

from .config import Config, apply_runtime_config
from .errors import register_error_handlers
from .tools.registry import get_available_tools


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config_overrides=None):
    """Create and configure a Toolmist application instance."""
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
        static_url_path="/static",
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    apply_runtime_config(app.config, config_overrides or {})

    from .blueprints.health import bp as health_bp
    from .blueprints.legacy import bp as legacy_bp
    from .blueprints.site import bp as site_bp

    app.register_blueprint(site_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(legacy_bp)
    register_error_handlers(app)

    app.extensions["toolmist_tools"] = get_available_tools()
    return app
