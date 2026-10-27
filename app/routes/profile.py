"""User profile route."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.audit import AuditLog

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile")
@login_required
def index():
    user_logs = (
        AuditLog.query.filter_by(actor_id=current_user.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return render_template("profile/index.html", logs=user_logs)
