"""Seed script to populate local development environment with synthetic data."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime, timezone, timedelta
import io
from app.extensions import db
from app.models.user import User, UserRole
from app.models.document import Document, DocumentCategory, DocumentPermission
from app.models.audit import AuditLog, AuditAction, AuditOutcome
from app.storage import get_storage


def seed_data(app):
    with app.app_context():
        db.create_all()

        # 1. Seed Users if not present
        users_data = [
            ("admin", "admin@portal.local", "AdminPass123!", UserRole.ADMIN),
            ("editor", "editor@portal.local", "EditorPass123!", UserRole.EDITOR),
            ("viewer", "viewer@portal.local", "ViewerPass123!", UserRole.VIEWER),
        ]

        user_objs = {}
        for username, email, password, role in users_data:
            u = User.query.filter_by(username=username).first()
            if not u:
                u = User(username=username, email=email, role=role, is_active_account=True)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
            user_objs[username] = u

        storage = get_storage()
        now = datetime.now(timezone.utc)

        # 2. Seed Synthetic Documents
        demo_docs = [
            {
                "title": "Cloud Architecture & Security Plan 2026",
                "description": "Comprehensive specifications for Azure App Service, Private Blob Storage, and Terraform IAC.",
                "category": DocumentCategory.TECHNICAL,
                "owner": user_objs["admin"],
                "filename": "cloud_architecture_2026.pdf",
                "ext": "pdf",
                "content": b"%PDF-1.4\n1 0 obj\n<< /Title (Cloud Architecture) /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF",
                "expiry": now + timedelta(days=90),
            },
            {
                "title": "Q3 Financial Performance Summary",
                "description": "Quarterly operational expenditure analysis and cloud infrastructure resource forecast.",
                "category": DocumentCategory.FINANCE,
                "owner": user_objs["editor"],
                "filename": "q3_financial_summary.txt",
                "ext": "txt",
                "content": b"FINANCIAL SUMMARY REPORT - Q3 2026\n=================================\nInfrastructure Costs: $120.45\nStatus: Verified\nAuditor: Finance Team",
                "expiry": now + timedelta(days=3),  # Expiring soon!
            },
            {
                "title": "Employee Data Privacy Policy (2025)",
                "description": "Legacy regulatory compliance terms superseded by modern GDPR/HIPAA standards.",
                "category": DocumentCategory.LEGAL,
                "owner": user_objs["admin"],
                "filename": "privacy_policy_2025_archive.txt",
                "ext": "txt",
                "content": b"DATA PRIVACY POLICY (SUPERSEDED)\nRetention Period: Expired\nAction: Archive only",
                "expiry": now - timedelta(days=10),  # Expired!
            },
            {
                "title": "Engineering Onboarding Handbook",
                "description": "Guides for local repository setup, Git branch conventions, and Jenkins CI/CD deployment.",
                "category": DocumentCategory.HR,
                "owner": user_objs["editor"],
                "filename": "onboarding_handbook.txt",
                "ext": "txt",
                "content": b"ENGINEERING ONBOARDING GUIDE\n1. Clone GitHub Repository\n2. Run local tests via pytest\n3. Review Jenkinsfile stages",
                "expiry": None,  # No expiry
            },
        ]

        for item in demo_docs:
            existing = Document.query.filter_by(title=item["title"]).first()
            if not existing:
                storage_id = f"demo_{item['filename']}"
                stream = io.BytesIO(item["content"])
                storage.save_file(
                    storage_id=storage_id,
                    file_stream=stream,
                    filename=item["filename"],
                    content_type="text/plain" if item["ext"] == "txt" else "application/pdf",
                )

                doc = Document(
                    title=item["title"],
                    description=item["description"],
                    category=item["category"],
                    owner_id=item["owner"].id,
                    storage_id=storage_id,
                    original_filename=item["filename"],
                    file_type=item["ext"],
                    file_size=len(item["content"]),
                    upload_timestamp=now - timedelta(days=2),
                    expiry_date=item["expiry"],
                )
                db.session.add(doc)
                db.session.commit()

                # Grant permission on the onboarding handbook to VIEWER role
                if item["title"] == "Engineering Onboarding Handbook":
                    perm = DocumentPermission(
                        document_id=doc.id,
                        role=UserRole.VIEWER,
                        can_download=True,
                        can_edit=False,
                        granted_by_id=user_objs["admin"].id,
                    )
                    db.session.add(perm)

                # Grant permission on Q3 Financial to viewer user
                if item["title"] == "Q3 Financial Performance Summary":
                    perm = DocumentPermission(
                        document_id=doc.id,
                        user_id=user_objs["viewer"].id,
                        can_download=True,
                        can_edit=False,
                        granted_by_id=user_objs["editor"].id,
                    )
                    db.session.add(perm)

                # Seed audit event
                log = AuditLog(
                    timestamp=now - timedelta(days=2),
                    actor_id=item["owner"].id,
                    actor_username=item["owner"].username,
                    action=AuditAction.DOCUMENT_UPLOAD,
                    document_id=doc.id,
                    outcome=AuditOutcome.SUCCESS,
                    ip_address="127.0.0.1",
                    details=f"Demo seed: uploaded {item['filename']}",
                )
                db.session.add(log)
                db.session.commit()


if __name__ == "__main__":
    from app import create_app

    app = create_app("development")
    seed_data(app)
    print("Local development database seeded successfully!")
