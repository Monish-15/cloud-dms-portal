"""Authentication routes: login, logout."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import authenticate_user
from app.services.audit_service import log_event
from app.models.audit import AuditAction, AuditOutcome

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user, message = authenticate_user(
            username=username,
            password=password,
            ip_address=request.remote_addr,
        )

        if user:
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))
        else:
            flash(message, "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_event(
        action=AuditAction.LOGOUT,
        outcome=AuditOutcome.SUCCESS,
        actor_id=current_user.id,
        actor_username=current_user.username,
        ip_address=request.remote_addr,
        details="User logged out",
    )
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
