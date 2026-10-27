"""Role-based authorization decorators."""

from functools import wraps
from flask import abort, request
from flask_login import current_user
from app.models.audit import AuditAction, AuditOutcome
from app.services.audit_service import log_event


def role_required(*allowed_roles):
    """Decorator ensuring current_user has at least one of the specified roles."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)

            if not current_user.has_role(*allowed_roles):
                log_event(
                    action=AuditAction.ACCESS_DENIED,
                    outcome=AuditOutcome.DENIED,
                    actor_id=current_user.id,
                    actor_username=current_user.username,
                    ip_address=request.remote_addr,
                    details=f"Denied access to {request.path}: requires {allowed_roles}, user has {current_user.role}",
                )
                return abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
