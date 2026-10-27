"""Document management, upload, download, and validation test suite."""

import io
from datetime import datetime, timezone
from app.models.document import Document, DocumentCategory, DocumentPermission
from app.storage import get_storage


def test_valid_pdf_upload_succeeds(client, editor_user):
    """Test valid PDF upload with appropriate headers."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Test) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

    response = client.post(
        "/documents/upload",
        data={
            "title": "Corporate Financial Audit",
            "category": DocumentCategory.FINANCE,
            "description": "Annual audit document for testing.",
            "file": (io.BytesIO(valid_pdf), "audit.pdf"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"uploaded successfully" in response.data
    assert b"Corporate Financial Audit" in response.data

    doc = Document.query.filter_by(title="Corporate Financial Audit").first()
    assert doc is not None
    assert doc.file_type == "pdf"
    assert doc.owner_id == editor_user.id
    assert get_storage().file_exists(doc.storage_id)


def test_valid_txt_upload_succeeds(client, editor_user):
    """Test valid text file upload."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    txt_content = b"Sample plain text file content for integration test."

    response = client.post(
        "/documents/upload",
        data={
            "title": "System Notes",
            "category": DocumentCategory.TECHNICAL,
            "description": "Technical notes.",
            "file": (io.BytesIO(txt_content), "notes.txt"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"uploaded successfully" in response.data
    assert b"System Notes" in response.data


def test_disallowed_extension_rejected(client, editor_user):
    """Executable or script files are strictly rejected."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    bad_file = b"echo 'Malicious payload'"

    response = client.post(
        "/documents/upload",
        data={
            "title": "Malicious Script",
            "category": DocumentCategory.GENERAL,
            "file": (io.BytesIO(bad_file), "exploit.sh"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"File extension .sh is not allowed" in response.data


def test_spoofed_pdf_content_rejected(client, editor_user):
    """Files with .pdf extension but invalid magic bytes are rejected."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    fake_pdf = b"This is plain ASCII text pretending to be a PDF file."

    response = client.post(
        "/documents/upload",
        data={
            "title": "Spoofed Document",
            "category": DocumentCategory.GENERAL,
            "file": (io.BytesIO(fake_pdf), "spoofed.pdf"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"File content does not match the expected .pdf format" in response.data


def test_download_authorized_document(client, editor_user, db):
    """Authorized users can download document stream."""
    content = b"Secret payload content for download test"
    storage = get_storage()
    storage_id = "test_download_file.txt"
    storage.save_file(storage_id, io.BytesIO(content), "sample.txt", "text/plain")

    doc = Document(
        title="Downloadable Doc",
        category=DocumentCategory.GENERAL,
        owner_id=editor_user.id,
        storage_id=storage_id,
        original_filename="sample.txt",
        file_type="txt",
        file_size=len(content),
        upload_timestamp=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()

    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    resp = client.get(f"/documents/{doc.id}/download")
    assert resp.status_code == 200
    assert resp.data == content
    assert "attachment" in resp.headers.get("Content-Disposition", "")


def test_download_nonexistent_document_returns_404_or_redirect(client, editor_user):
    """Attempting to download nonexistent document returns appropriate error."""
    client.post("/login", data={"username": "editor_test", "password": "EditorPass123!"})
    resp = client.get("/documents/99999/download", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Document not found" in resp.data


def test_shared_permission_allows_viewer_download(client, viewer_user, editor_user, db):
    """A viewer granted explicit permission can download the document."""
    content = b"Shared knowledge base document"
    storage = get_storage()
    storage_id = "shared_doc.txt"
    storage.save_file(storage_id, io.BytesIO(content), "shared.txt", "text/plain")

    doc = Document(
        title="Shared Knowledge Base",
        category=DocumentCategory.TECHNICAL,
        owner_id=editor_user.id,
        storage_id=storage_id,
        original_filename="shared.txt",
        file_type="txt",
        file_size=len(content),
        upload_timestamp=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()

    # Before granting permission, viewer cannot download
    client.post("/login", data={"username": "viewer_test", "password": "ViewerPass123!"})
    resp_denied = client.get(f"/documents/{doc.id}/download")
    assert resp_denied.status_code == 403

    # Grant permission to viewer
    perm = DocumentPermission(
        document_id=doc.id,
        user_id=viewer_user.id,
        can_download=True,
        can_edit=False,
        granted_by_id=editor_user.id,
    )
    db.session.add(perm)
    db.session.commit()

    # Now viewer can download
    resp_allowed = client.get(f"/documents/{doc.id}/download")
    assert resp_allowed.status_code == 200
    assert resp_allowed.data == content


def test_admin_can_delete_document(client, admin_user, editor_user, db):
    """Admin can delete documents from storage and database."""
    content = b"Content to be deleted"
    storage = get_storage()
    storage_id = "doc_to_delete.txt"
    storage.save_file(storage_id, io.BytesIO(content), "delete_me.txt", "text/plain")

    doc = Document(
        title="Delete Me",
        category=DocumentCategory.GENERAL,
        owner_id=editor_user.id,
        storage_id=storage_id,
        original_filename="delete_me.txt",
        file_type="txt",
        file_size=len(content),
        upload_timestamp=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.commit()

    client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"})
    resp = client.post(f"/documents/{doc.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Document deleted successfully" in resp.data

    # Verify soft-deleted
    assert Document.query.get(doc.id).is_deleted is True
    # Verify file deleted from storage
    assert not storage.file_exists(storage_id)
