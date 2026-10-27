"""Audit log model for recording security-critical events."""

from datetime import datetime, timezone
from app.extensions import db


class AuditAction:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD"
    DOCUMENT_UPDATE = "DOCUMENT_UPDATE"
    DOCUMENT_DELETE = "DOCUMENT_DELETE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    USER_CREATE = "USER_CREATE"
    USER_STATUS_CHANGE = "USER_STATUS_CHANGE"
    USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
    ACCESS_DENIED = "ACCESS_DENIED"


class AuditOutcome:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    actor_id = db.Column(db.Integer, nullable=True)  # None if unauthenticated
    actor_username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    document_id = db.Column(db.Integer, nullable=True, index=True)
    outcome = db.Column(db.String(20), nullable=False, default=AuditOutcome.SUCCESS)
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f"<AuditLog {self.id} | {self.action} | {self.actor_username} | {self.outcome}>"
