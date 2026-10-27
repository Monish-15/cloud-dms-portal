"""Document and DocumentPermission models."""

from datetime import datetime, timezone, timedelta
from app.extensions import db


class DocumentCategory:
    FINANCE = "Finance"
    LEGAL = "Legal"
    HR = "Human Resources"
    TECHNICAL = "Technical"
    GENERAL = "General"

    ALL_CATEGORIES = [FINANCE, LEGAL, HR, TECHNICAL, GENERAL]


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default=DocumentCategory.GENERAL)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    storage_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    original_filename = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # pdf, docx, xlsx, txt
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    upload_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    permissions = db.relationship(
        "DocumentPermission",
        backref="document",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def is_expired(self) -> bool:
        """Return True if document has an expiry date that has passed."""
        if not self.expiry_date:
            return False
        now_utc = datetime.now(timezone.utc)
        exp_dt = self.expiry_date
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return now_utc >= exp_dt

    @property
    def is_expiring_soon(self) -> bool:
        """Return True if document expires within the next 7 days and is not yet expired."""
        if not self.expiry_date or self.is_expired:
            return False
        now_utc = datetime.now(timezone.utc)
        exp_dt = self.expiry_date
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return (exp_dt - now_utc) <= timedelta(days=7)

    @property
    def formatted_size(self) -> str:
        """Human-readable file size."""
        size = float(self.file_size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"


class DocumentPermission(db.Model):
    __tablename__ = "document_permissions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    role = db.Column(db.String(20), nullable=True)  # e.g. "VIEWER" or "EDITOR"
    can_download = db.Column(db.Boolean, default=True, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)
    granted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="granted_permissions")
    granted_by = db.relationship("User", foreign_keys=[granted_by_id])

    def __repr__(self):
        target = f"User {self.user_id}" if self.user_id else f"Role {self.role}"
        return f"<DocumentPermission Doc:{self.document_id} -> {target}>"
