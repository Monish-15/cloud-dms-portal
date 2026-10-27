"""Admin-only routes for user management and audit logging."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.user import User, UserRole
from app.models.audit import AuditLog, AuditAction
from app.services.auth_service import create_user, update_user_status, update_user_role
from app.routes.decorators import role_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN)
def users():
    """User management dashboard."""
    if request.method == "POST":
        action = request.form.get("action")

        if action == "create":
            username = request.form.get("username", "")
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            role = request.form.get("role", UserRole.VIEWER)

            new_user, msg = create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                creator=current_user,
                ip_address=request.remote_addr,
            )
            if new_user:
                flash(msg, "success")
            else:
                flash(msg, "danger")

        elif action == "toggle_status":
            user_id = request.form.get("user_id", type=int)
            is_active = request.form.get("is_active") == "true"
            success, msg = update_user_status(
                target_user_id=user_id,
                is_active=is_active,
                admin_user=current_user,
                ip_address=request.remote_addr,
            )
            flash(msg, "success" if success else "danger")

        elif action == "update_role":
            user_id = request.form.get("user_id", type=int)
            new_role = request.form.get("role")
            success, msg = update_user_role(
                target_user_id=user_id,
                new_role=new_role,
                admin_user=current_user,
                ip_address=request.remote_addr,
            )
            flash(msg, "success" if success else "danger")

        return redirect(url_for("admin.users"))

    all_users = User.query.order_by(User.id.asc()).all()
    return render_template(
        "admin/users.html",
        users=all_users,
        roles=UserRole.ALL_ROLES,
    )


@admin_bp.route("/audit")
@login_required
@role_required(UserRole.ADMIN)
def audit_logs():
    """Audit log viewer with filtering and pagination."""
    action_filter = request.args.get("action", "").strip()
    outcome_filter = request.args.get("outcome", "").strip()
    username_filter = request.args.get("username", "").strip()
    page = request.args.get("page", 1, type=int)

    q = AuditLog.query

    if action_filter:
        q = q.filter(AuditLog.action == action_filter)

    if outcome_filter:
        q = q.filter(AuditLog.outcome == outcome_filter)

    if username_filter:
        q = q.filter(AuditLog.actor_username.ilike(f"%{username_filter}%"))

    logs_paginated = q.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    all_actions = [
        AuditAction.LOGIN_SUCCESS,
        AuditAction.LOGIN_FAILURE,
        AuditAction.LOGOUT,
        AuditAction.DOCUMENT_UPLOAD,
        AuditAction.DOCUMENT_DOWNLOAD,
        AuditAction.DOCUMENT_UPDATE,
        AuditAction.DOCUMENT_DELETE,
        AuditAction.PERMISSION_CHANGE,
        AuditAction.USER_CREATE,
        AuditAction.USER_STATUS_CHANGE,
        AuditAction.USER_ROLE_CHANGE,
        AuditAction.ACCESS_DENIED,
    ]

    return render_template(
        "admin/audit.html",
        pagination=logs_paginated,
        actions=all_actions,
        current_action=action_filter,
        current_outcome=outcome_filter,
        current_username=username_filter,
    )
