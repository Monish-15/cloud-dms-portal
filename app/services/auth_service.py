"""Authentication and user management service."""

from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from flask import current_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.audit import AuditAction, AuditOutcome
from app.services.audit_service import log_event


def authenticate_user(username: str, password: str, ip_address: str = None) -> Tuple[Optional[User], str]:
    """Authenticate a user with brute-force lockout protection.

    Returns (user, message).
    """
    if not username or not password:
        return None, "Username and password are required."

    user = User.query.filter_by(username=username.strip()).first()
    if not user:
        log_event(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            actor_username=username,
            ip_address=ip_address,
            details="Login failed: user not found",
        )
        return None, "Invalid username or password."

    # Check if account is inactive
    if not user.is_active_account:
        log_event(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.DENIED,
            actor_id=user.id,
            actor_username=user.username,
            ip_address=ip_address,
            details="Login denied: account is deactivated",
        )
        return None, "This account has been deactivated. Please contact an administrator."

    # Check if locked out
    if user.is_locked():
        lockout_expiry = user.locked_until
        if lockout_expiry and lockout_expiry.tzinfo is None:
            lockout_expiry = lockout_expiry.replace(tzinfo=timezone.utc)
        remaining = int((lockout_expiry - datetime.now(timezone.utc)).total_seconds() / 60) + 1
        log_event(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.DENIED,
            actor_id=user.id,
            actor_username=user.username,
            ip_address=ip_address,
            details=f"Login blocked: account locked for {remaining} more minutes",
        )
        return None, f"Account is temporarily locked. Try again in {remaining} minute(s)."

    # Verify password
    if not user.check_password(password):
        user.failed_login_attempts += 1
        max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        lockout_mins = current_app.config.get("LOGIN_LOCKOUT_MINUTES", 15)

        msg = "Invalid username or password."
        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_mins)
            msg = f"Too many failed login attempts. Account locked for {lockout_mins} minutes."

        db.session.commit()
        log_event(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            actor_id=user.id,
            actor_username=user.username,
            ip_address=ip_address,
            details=f"Failed attempt {user.failed_login_attempts}/{max_attempts}",
        )
        return None, msg

    # Successful login: reset failed counter and clear lock
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    log_event(
        action=AuditAction.LOGIN_SUCCESS,
        outcome=AuditOutcome.SUCCESS,
        actor_id=user.id,
        actor_username=user.username,
        ip_address=ip_address,
        details="Login successful",
    )
    return user, "Login successful."


def create_user(
    username: str,
    email: str,
    password: str,
    role: str = UserRole.VIEWER,
    is_active: bool = True,
    creator: User = None,
    ip_address: str = None,
) -> Tuple[Optional[User], str]:
    """Create a new user with validation."""
    username = username.strip()
    email = email.strip().lower()

    if not username or len(username) < 3:
        return None, "Username must be at least 3 characters long."

    if not email or "@" not in email:
        return None, "A valid email address is required."

    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters long."

    if role not in UserRole.ALL_ROLES:
        return None, f"Invalid role. Choose from: {', '.join(UserRole.ALL_ROLES)}"

    if User.query.filter_by(username=username).first():
        return None, "Username is already registered."

    if User.query.filter_by(email=email).first():
        return None, "Email address is already in use."

    user = User(
        username=username,
        email=email,
        role=role,
        is_active_account=is_active,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    log_event(
        action=AuditAction.USER_CREATE,
        outcome=AuditOutcome.SUCCESS,
        actor_id=creator.id if creator else None,
        actor_username=creator.username if creator else "system",
        ip_address=ip_address,
        details=f"Created user {username} with role {role}",
    )
    return user, "User created successfully."


def update_user_status(
    target_user_id: int, is_active: bool, admin_user: User, ip_address: str = None
) -> Tuple[bool, str]:
    """Activate or deactivate a user account."""
    if not admin_user.is_admin():
        return False, "Unauthorized action."

    user = User.query.get(target_user_id)
    if not user:
        return False, "User not found."

    # Guard: prevent deactivating the last active administrator
    if user.is_admin() and not is_active:
        active_admins = User.query.filter_by(role=UserRole.ADMIN, is_active_account=True).count()
        if active_admins <= 1:
            return False, "Cannot deactivate the last active administrator."

    user.is_active_account = is_active
    db.session.commit()

    action_label = "activated" if is_active else "deactivated"
    log_event(
        action=AuditAction.USER_STATUS_CHANGE,
        outcome=AuditOutcome.SUCCESS,
        actor_id=admin_user.id,
        actor_username=admin_user.username,
        ip_address=ip_address,
        details=f"User {user.username} {action_label}",
    )
    return True, f"User {user.username} has been {action_label}."


def update_user_role(
    target_user_id: int, new_role: str, admin_user: User, ip_address: str = None
) -> Tuple[bool, str]:
    """Change a user's role."""
    if not admin_user.is_admin():
        return False, "Unauthorized action."

    if new_role not in UserRole.ALL_ROLES:
        return False, "Invalid role specified."

    user = User.query.get(target_user_id)
    if not user:
        return False, "User not found."

    # Guard: prevent removing the last admin's admin role
    if user.is_admin() and new_role != UserRole.ADMIN:
        active_admins = User.query.filter_by(role=UserRole.ADMIN, is_active_account=True).count()
        if active_admins <= 1:
            return False, "Cannot demote the last administrator."

    old_role = user.role
    user.role = new_role
    db.session.commit()

    log_event(
        action=AuditAction.USER_ROLE_CHANGE,
        outcome=AuditOutcome.SUCCESS,
        actor_id=admin_user.id,
        actor_username=admin_user.username,
        ip_address=ip_address,
        details=f"Changed {user.username} role from {old_role} to {new_role}",
    )
    return True, f"Role for {user.username} updated to {new_role}."
