"""Security headers, session security, and IDOR protection test suite."""

import io
from datetime import datetime, timezone
from app.models.document import Document, DocumentCategory
from app.storage import get_storage


def test_security_headers_present(client):
    """Test that all responses include strict HTTP security headers."""
    response = client.get("/login")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "1; mode=block" in response.headers.get("X-XSS-Protection", "")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_cookie_security_flags(client, admin_user):
    """Test that session cookie is configured with HttpOnly and SameSite."""
    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    cookie = client.get_cookie("session")
    if cookie:
        assert cookie.http_only is True
        assert cookie.same_site in ("Lax", "Strict")


def test_idor_protection_direct_document_access(client, editor_user, viewer_user, db):
    """Test that Viewer cannot access or download Editor's document directly via URL manipulation (IDOR)."""
    # 1. Editor creates a private document
    content = b"Confidential financial statement"
    storage = get_storage()
    storage_id = "private_financial_doc.txt"
    storage.save_file(storage_id, io.BytesIO(content), "confidential.txt", "text/plain")

    doc = Document(
        title="Confidential Financial Statement",
        description="Internal only.",
        category=DocumentCategory.FINANCE,
        owner_id=editor_user.id,
        storage_id=storage_id,
        original_filename="confidential.txt",
        file_type="txt",
        file_size=len(content),
        upload_timestamp=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()

    # 2. Login as Viewer and attempt to view details
    client.post("/login", data={"username": "viewer_test", "password": "ViewerPass123!"})
    resp_view = client.get(f"/documents/{doc.id}")
    assert resp_view.status_code == 403

    # 3. Attempt to download directly via ID
    resp_download = client.get(f"/documents/{doc.id}/download")
    assert resp_download.status_code == 403


def test_path_traversal_sanitization(client, editor_user):
    """Filenames with path traversal characters (../) are sanitized safely."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    content = b"Safe file content"

    resp = client.post(
        "/documents/upload",
        data={
            "title": "Traversal Test",
            "category": DocumentCategory.GENERAL,
            "file": (io.BytesIO(content), "../../../etc/passwd.txt"),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    doc = Document.query.filter_by(title="Traversal Test").first()
    assert doc is not None
    # Secure filename should have stripped directory traversal
    assert "/" not in doc.original_filename
    assert "\\" not in doc.original_filename
    assert ".." not in doc.original_filename
