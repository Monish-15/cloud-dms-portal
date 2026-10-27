"""Dashboard routes: overview metrics and quick access."""

from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.document import Document
from app.models.audit import AuditLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    # Base query according to role
    if current_user.is_admin():
        base_query = Document.query.filter_by(is_deleted=False)
    elif current_user.is_editor():
        base_query = Document.query.filter(
            Document.is_deleted.is_(False),
            Document.owner_id == current_user.id,
        )
    else:  # VIEWER
        # accessible documents via permission or public
        base_query = Document.query.filter(
            Document.is_deleted.is_(False),
            Document.owner_id == current_user.id,
        )

    all_docs = base_query.all()
    total_docs = len(all_docs)
    total_bytes = sum(d.file_size for d in all_docs)

    expiring_soon_docs = [d for d in all_docs if d.is_expiring_soon]
    expired_docs = [d for d in all_docs if d.is_expired]

    # Format storage size
    size_str = "0 B"
    if total_bytes > 0:
        size = float(total_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                size_str = f"{size:.1f} {unit}"
                break
            size /= 1024.0

    # Recent activities (Admin sees all, others see their own)
    if current_user.is_admin():
        recent_activity = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    else:
        recent_activity = (
            AuditLog.query.filter_by(actor_id=current_user.id)
            .order_by(AuditLog.timestamp.desc())
            .limit(8)
            .all()
        )

    recent_uploads = (
        base_query.order_by(Document.upload_timestamp.desc()).limit(5).all()
    )

    return render_template(
        "dashboard/index.html",
        total_docs=total_docs,
        total_storage=size_str,
        expiring_soon_count=len(expiring_soon_docs),
        expired_count=len(expired_docs),
        expiring_soon_docs=expiring_soon_docs[:5],
        recent_uploads=recent_uploads,
        recent_activity=recent_activity,
    )
