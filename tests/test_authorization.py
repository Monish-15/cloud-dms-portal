"""Role-based authorization and permission test suite."""

from app.models.document import Document, DocumentCategory
from datetime import datetime, timezone


def test_admin_can_access_user_management(client, admin_user):
    """Admin can view user management interface."""
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"User Management" in response.data


def test_editor_denied_from_user_management(client, editor_user):
    """Editor is rejected with HTTP 403 when requesting admin endpoints."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_viewer_denied_from_user_management(client, viewer_user):
    """Viewer is rejected with HTTP 403 when requesting admin endpoints."""
    client.post("/login", data={"username": "viewer_test", "password": "ViewerPass123!"})
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_admin_can_access_audit_logs(client, admin_user):
    """Admin can view the security audit trail."""
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    response = client.get("/admin/audit")
    assert response.status_code == 200
    assert b"Security Audit Trail" in response.data


def test_editor_denied_from_audit_logs(client, editor_user):
    """Editor is forbidden from viewing audit trail."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    response = client.get("/admin/audit")
    assert response.status_code == 403


def test_viewer_denied_from_audit_logs(client, viewer_user):
    """Viewer is forbidden from viewing audit trail."""
    client.post("/login", data={"username": "viewer_test", "password": "ViewerPass123!"})
    response = client.get("/admin/audit")
    assert response.status_code == 403


def test_editor_and_admin_can_access_upload_page(client, editor_user, admin_user):
    """Admin and Editor roles can access document upload endpoint."""
    # Editor check
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    resp_editor = client.get("/documents/upload")
    assert resp_editor.status_code == 200

    client.get("/logout")

    # Admin check
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    resp_admin = client.get("/documents/upload")
    assert resp_admin.status_code == 200


def test_viewer_denied_from_upload_page(client, viewer_user):
    """Viewer role is rejected from uploading documents."""
    client.post("/login", data={"username": "viewer_test", "password": "ViewerPass123!"})
    response = client.get("/documents/upload")
    assert response.status_code == 403


def test_non_admin_cannot_delete_document(client, editor_user, admin_user, db):
    """Editors cannot delete documents, even if they own them."""
    # Create doc owned by editor
    doc = Document(
        title="Editor Doc",
        category=DocumentCategory.GENERAL,
        owner_id=editor_user.id,
        storage_id="test_del_doc.txt",
        original_filename="test_del_doc.txt",
        file_type="txt",
        file_size=10,
        upload_timestamp=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()

    # Login as editor and attempt delete
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    resp = client.post(f"/documents/{doc.id}/delete")
    assert resp.status_code == 403

    # Verify doc still exists
    assert Document.query.get(doc.id).is_deleted is False


def test_cannot_deactivate_last_active_admin(client, admin_user, db):
    """Safeguard prevents accidental deactivation of the sole remaining admin."""
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    resp = client.post(
        "/admin/users",
        data={
            "action": "toggle_status",
            "user_id": admin_user.id,
            "is_active": "false",
        },
        follow_redirects=True,
    )
    assert b"Cannot deactivate the last active administrator" in resp.data
    assert admin_user.is_active_account is True
