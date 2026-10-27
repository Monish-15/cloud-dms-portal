"""Routes module registering blueprints."""

from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.documents import documents_bp
from app.routes.admin import admin_bp
from app.routes.profile import profile_bp
from app.routes.errors import errors_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "documents_bp",
    "admin_bp",
    "profile_bp",
    "errors_bp",
]
