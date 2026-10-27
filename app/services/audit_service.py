"""Audit logging service for tracking system security events."""

from datetime import datetime, timezone
import logging
from app.extensions import db
from app.models.audit import AuditLog, AuditOutcome

logger = logging.getLogger(__name__)


def log_event(
    action: str,
    outcome: str = AuditOutcome.SUCCESS,
    actor_id: int = None,
    actor_username: str = None,
    document_id: int = None,
    ip_address: str = None,
    details: str = None,
) -> AuditLog:
    """Create and persist an audit log entry.

    Never logs passwords or secret data.
    """
    try:
        # Sanitize details to prevent accidental credential leakage
        safe_details = details[:500] if details else None
        if safe_details and any(k in safe_details.lower() for k in ("password", "token", "secret", "key")):
            safe_details = "[REDACTED_FOR_SECURITY]"

        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_username=actor_username[:64] if actor_username else None,
            action=action,
            document_id=document_id,
            outcome=outcome,
            ip_address=ip_address[:45] if ip_address else None,
            details=safe_details,
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    except Exception as e:
        logger.error("Failed to write audit log entry: %s", e)
        db.session.rollback()
        return None
