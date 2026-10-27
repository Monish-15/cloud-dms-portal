"""User model with secure password hashing and account status handling."""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db


class UserRole:
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

    ALL_ROLES = [ADMIN, EDITOR, VIEWER]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.VIEWER)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    documents = db.relationship("Document", backref="owner", lazy="dynamic", foreign_keys="Document.owner_id")

    @property
    def is_active(self):
        """Flask-Login property: checks if account is active and not locked."""
        return self.is_active_account and not self.is_locked()

    def set_password(self, password: str):
        """Hash and store password using pbkdf2:sha256."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify plain text password against hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is temporarily locked due to failed login attempts."""
        if self.locked_until:
            now_utc = datetime.now(timezone.utc)
            # handle naive vs aware
            locked_until_dt = self.locked_until
            if locked_until_dt.tzinfo is None:
                locked_until_dt = locked_until_dt.replace(tzinfo=timezone.utc)
            return now_utc < locked_until_dt
        return False

    def has_role(self, *roles: str) -> bool:
        """Check if user belongs to any of the requested roles."""
        return self.role in roles

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_editor(self) -> bool:
        return self.role == UserRole.EDITOR

    def is_viewer(self) -> bool:
        return self.role == UserRole.VIEWER

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
