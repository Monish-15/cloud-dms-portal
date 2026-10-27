"""Audit logging verification test suite."""

import io
from app.models.audit import AuditLog, AuditAction, AuditOutcome
from app.services.audit_service import log_event
from app.models.document import DocumentCategory


def test_login_events_generate_audit_records(client, admin_user):
    """Successful and failed logins generate corresponding audit entries."""
    # 1. Failed login
    client.post("/login", data={"username": "admin_test", "password": "WrongPassword"})
    failed_log = (
        AuditLog.query.filter_by(action=AuditAction.LOGIN_FAILURE)
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert failed_log is not None
    assert failed_log.actor_username == "admin_test"
    assert failed_log.outcome == AuditOutcome.FAILURE

    # 2. Successful login
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    success_log = (
        AuditLog.query.filter_by(action=AuditAction.LOGIN_SUCCESS)
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert success_log is not None
    assert success_log.actor_username == "admin_test"
    assert success_log.outcome == AuditOutcome.SUCCESS


def test_document_upload_generates_audit_record(client, editor_user):
    """Uploading a document generates an immutable audit record."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    txt_content = b"Audit test file payload."

    client.post(
        "/documents/upload",
        data={
            "title": "Audit Subject",
            "category": DocumentCategory.GENERAL,
            "file": (io.BytesIO(txt_content), "audit_file.txt"),
        },
    )

    upload_log = (
        AuditLog.query.filter_by(action=AuditAction.DOCUMENT_UPLOAD)
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert upload_log is not None
    assert upload_log.actor_username == "editor_test"
    assert "audit_file.txt" in upload_log.details


def test_audit_sanitizes_passwords_and_secrets(app):
    """Audit service proactively redacts strings containing secrets or password tokens."""
    with app.app_context():
        log_entry = log_event(
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            actor_username="test_actor",
            details="User entered password=SuperSecretPassword123!",
        )
        assert "SuperSecretPassword123!" not in log_entry.details
        assert "[REDACTED_FOR_SECURITY]" in log_entry.details
