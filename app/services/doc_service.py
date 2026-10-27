"""Document service for upload, download, metadata management, and authorization."""

import uuid
from datetime import datetime, timezone
from typing import Tuple, Optional, BinaryIO
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.user import User, UserRole
from app.models.document import Document, DocumentCategory, DocumentPermission
from app.models.audit import AuditAction, AuditOutcome
from app.services.audit_service import log_event
from app.storage import get_storage

# Allowed extensions and magic byte headers
MAGIC_HEADERS = {
    "pdf": [b"%PDF-"],
    "docx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
}


def validate_file_content(file_storage, filename: str) -> Tuple[bool, str, str]:
    """Validate file extension and examine magic bytes to prevent spoofed uploads.

    Returns (is_valid, ext, error_message).
    """
    if not filename or "." not in filename:
        return False, "", "File must have a valid extension."

    ext = filename.rsplit(".", 1)[1].lower()
    allowed_exts = {"pdf", "docx", "xlsx", "txt"}
    if ext not in allowed_exts:
        return False, "", f"File extension .{ext} is not allowed. Allowed: {', '.join(allowed_exts)}."

    # Read the first 512 bytes for inspection
    file_storage.seek(0)
    header = file_storage.read(512)
    file_storage.seek(0)

    if not header:
        return False, "", "Uploaded file is empty."

    if ext in MAGIC_HEADERS:
        expected_prefixes = MAGIC_HEADERS[ext]
        if not any(header.startswith(p) for p in expected_prefixes):
            return False, "", f"File content does not match the expected .{ext} format."
    elif ext == "txt":
        # Check that it is valid plain text without null bytes
        if b"\x00" in header:
            return False, "", "Binary file detected; not a valid text file."
        try:
            header.decode("utf-8")
        except UnicodeDecodeError:
            try:
                header.decode("latin-1")
            except Exception:
                return False, "", "File is not valid text."

    return True, ext, ""


def can_user_access_document(
    document: Document, user: User, operation: str = "view"
) -> bool:
    """Authorize document operations according to RBAC and permissions.

    operation: 'view', 'download', 'edit', 'delete'
    """
    if not user or not user.is_active:
        return False

    # Admins have full access to all non-deleted documents
    if user.is_admin():
        return True

    # Deleted documents can only be accessed by admin
    if document.is_deleted:
        return False

    # Check ownership
    is_owner = (document.owner_id == user.id)

    if operation == "delete":
        # Only admin is allowed to delete documents
        return False

    if operation in ("view", "download"):
        # Document expiry check: ordinary users cannot download expired documents
        if operation == "download" and document.is_expired and not is_owner:
            return False

        if is_owner:
            return True

        # Check explicit permissions assigned to user or their role
        has_perm = DocumentPermission.query.filter(
            DocumentPermission.document_id == document.id,
            db.or_(
                DocumentPermission.user_id == user.id,
                DocumentPermission.role == user.role,
                DocumentPermission.role == "ALL",
            ),
            DocumentPermission.can_download if operation == "download" else True,
        ).first()

        return has_perm is not None

    if operation == "edit":
        if is_owner and user.is_editor():
            return True
        # Check explicit edit permission
        has_edit_perm = DocumentPermission.query.filter(
            DocumentPermission.document_id == document.id,
            db.or_(
                DocumentPermission.user_id == user.id,
                DocumentPermission.role == user.role,
            ),
            DocumentPermission.can_edit.is_(True),
        ).first()
        return has_edit_perm is not None

    return False


def upload_document(
    title: str,
    description: str,
    category: str,
    file_storage,
    owner: User,
    expiry_date: Optional[datetime] = None,
    ip_address: str = None,
) -> Tuple[Optional[Document], str]:
    """Process file upload, save file securely to storage, and create database record."""
    if not owner.has_role(UserRole.ADMIN, UserRole.EDITOR):
        log_event(
            action=AuditAction.DOCUMENT_UPLOAD,
            outcome=AuditOutcome.DENIED,
            actor_id=owner.id,
            actor_username=owner.username,
            ip_address=ip_address,
            details="Upload denied: insufficient permissions (VIEWER role)",
        )
        return None, "Only Administrators and Editors are permitted to upload documents."

    title = title.strip()
    if not title:
        return None, "Document title is required."

    if category not in DocumentCategory.ALL_CATEGORIES:
        return None, f"Invalid category. Choose from: {', '.join(DocumentCategory.ALL_CATEGORIES)}"

    raw_filename = file_storage.filename or "document"
    clean_filename = secure_filename(raw_filename)
    if not clean_filename:
        clean_filename = f"upload_{uuid.uuid4().hex[:8]}.txt"

    is_valid, ext, err_msg = validate_file_content(file_storage, clean_filename)
    if not is_valid:
        return None, err_msg

    # Generate isolated storage identifier
    storage_id = f"{uuid.uuid4().hex}.{ext}"

    # Determine MIME type
    mime_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "txt": "text/plain",
    }
    content_type = mime_types.get(ext, "application/octet-stream")

    try:
        storage = get_storage()
        file_storage.seek(0)
        bytes_written = storage.save_file(
            storage_id=storage_id,
            file_stream=file_storage.stream,
            filename=clean_filename,
            content_type=content_type,
        )

        doc = Document(
            title=title,
            description=description.strip() if description else "",
            category=category,
            owner_id=owner.id,
            storage_id=storage_id,
            original_filename=clean_filename,
            file_type=ext,
            file_size=bytes_written,
            upload_timestamp=datetime.now(timezone.utc),
            expiry_date=expiry_date,
        )

        db.session.add(doc)
        db.session.commit()

        log_event(
            action=AuditAction.DOCUMENT_UPLOAD,
            outcome=AuditOutcome.SUCCESS,
            actor_id=owner.id,
            actor_username=owner.username,
            document_id=doc.id,
            ip_address=ip_address,
            details=f"Uploaded '{clean_filename}' ({doc.formatted_size}) under category '{category}'",
        )
        return doc, "Document uploaded successfully."
    except Exception as e:
        db.session.rollback()
        # Clean up storage file if written
        try:
            get_storage().delete_file(storage_id)
        except Exception:
            pass
        return None, f"Upload failed: {str(e)}"


def get_document_for_download(
    document_id: int, user: User, ip_address: str = None
) -> Tuple[Optional[BinaryIO], Optional[Document], str, str]:
    """Retrieve document stream and metadata verifying authorization.

    Returns (stream, doc, content_type, error_msg).
    """
    doc = Document.query.get(document_id)
    if not doc or doc.is_deleted:
        log_event(
            action=AuditAction.DOCUMENT_DOWNLOAD,
            outcome=AuditOutcome.FAILURE,
            actor_id=user.id if user else None,
            actor_username=user.username if user else "anonymous",
            document_id=document_id,
            ip_address=ip_address,
            details="Download failed: document not found",
        )
        return None, None, "", "Document not found."

    if not can_user_access_document(doc, user, operation="download"):
        log_event(
            action=AuditAction.DOCUMENT_DOWNLOAD,
            outcome=AuditOutcome.DENIED,
            actor_id=user.id,
            actor_username=user.username,
            document_id=document_id,
            ip_address=ip_address,
            details="Download denied: unauthorized or expired document",
        )
        return None, None, "", "Access denied: you do not have permission to download this document."

    try:
        storage = get_storage()
        stream, content_type = storage.get_file_stream(doc.storage_id)

        log_event(
            action=AuditAction.DOCUMENT_DOWNLOAD,
            outcome=AuditOutcome.SUCCESS,
            actor_id=user.id,
            actor_username=user.username,
            document_id=document_id,
            ip_address=ip_address,
            details=f"Downloaded '{doc.original_filename}'",
        )
        return stream, doc, content_type, ""
    except FileNotFoundError:
        return None, None, "", "File not found in storage repository."
    except Exception as e:
        return None, None, "", f"Storage error: {str(e)}"


def delete_document(
    document_id: int, user: User, ip_address: str = None
) -> Tuple[bool, str]:
    """Delete document (admin only)."""
    if not user.is_admin():
        log_event(
            action=AuditAction.DOCUMENT_DELETE,
            outcome=AuditOutcome.DENIED,
            actor_id=user.id,
            actor_username=user.username,
            document_id=document_id,
            ip_address=ip_address,
            details="Delete denied: only administrators can delete documents",
        )
        return False, "Access denied: only administrators can delete documents."

    doc = Document.query.get(document_id)
    if not doc or doc.is_deleted:
        return False, "Document not found."

    try:
        # Remove from storage
        get_storage().delete_file(doc.storage_id)
        # Mark as deleted or remove record
        doc.is_deleted = True
        db.session.commit()

        log_event(
            action=AuditAction.DOCUMENT_DELETE,
            outcome=AuditOutcome.SUCCESS,
            actor_id=user.id,
            actor_username=user.username,
            document_id=doc.id,
            ip_address=ip_address,
            details=f"Deleted document '{doc.title}' ({doc.original_filename})",
        )
        return True, "Document deleted successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to delete document: {str(e)}"


def update_document_metadata(
    document_id: int,
    title: str,
    description: str,
    category: str,
    expiry_date: Optional[datetime],
    user: User,
    ip_address: str = None,
) -> Tuple[bool, str]:
    """Update metadata for an existing document."""
    doc = Document.query.get(document_id)
    if not doc or doc.is_deleted:
        return False, "Document not found."

    if not can_user_access_document(doc, user, operation="edit"):
        log_event(
            action=AuditAction.DOCUMENT_UPDATE,
            outcome=AuditOutcome.DENIED,
            actor_id=user.id,
            actor_username=user.username,
            document_id=document_id,
            ip_address=ip_address,
            details="Update denied: lacking edit permission",
        )
        return False, "Access denied: you do not have permission to edit this document."

    title = title.strip()
    if not title:
        return False, "Document title cannot be empty."

    if category not in DocumentCategory.ALL_CATEGORIES:
        return False, "Invalid category."

    doc.title = title
    doc.description = description.strip() if description else ""
    doc.category = category
    doc.expiry_date = expiry_date
    db.session.commit()

    log_event(
        action=AuditAction.DOCUMENT_UPDATE,
        outcome=AuditOutcome.SUCCESS,
        actor_id=user.id,
        actor_username=user.username,
        document_id=doc.id,
        ip_address=ip_address,
        details=f"Updated metadata for document '{doc.title}'",
    )
    return True, "Document updated successfully."
