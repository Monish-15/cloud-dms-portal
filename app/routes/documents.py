"""Document management routes."""

from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    send_file,
    abort,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.document import Document, DocumentCategory, DocumentPermission
from app.models.user import User, UserRole
from app.models.audit import AuditAction, AuditOutcome
from app.services.doc_service import (
    upload_document,
    get_document_for_download,
    delete_document,
    update_document_metadata,
    can_user_access_document,
)
from app.services.audit_service import log_event
from app.routes.decorators import role_required

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/")
@login_required
def list_documents():
    """Document library with category, expiry, and text search filters."""
    query_str = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    expiry_filter = request.args.get("expiry", "all").strip()
    page = request.args.get("page", 1, type=int)

    # Base query
    if current_user.is_admin():
        q = Document.query.filter_by(is_deleted=False)
    else:
        # User owns the document OR has an explicit permission
        shared_doc_ids = db.session.query(DocumentPermission.document_id).filter(
            db.or_(
                DocumentPermission.user_id == current_user.id,
                DocumentPermission.role == current_user.role,
                DocumentPermission.role == "ALL",
            )
        )
        q = Document.query.filter(
            Document.is_deleted.is_(False),
            db.or_(
                Document.owner_id == current_user.id,
                Document.id.in_(shared_doc_ids),
            ),
        )

    # Search filter
    if query_str:
        q = q.filter(
            db.or_(
                Document.title.ilike(f"%{query_str}%"),
                Document.description.ilike(f"%{query_str}%"),
                Document.original_filename.ilike(f"%{query_str}%"),
            )
        )

    # Category filter
    if category and category in DocumentCategory.ALL_CATEGORIES:
        q = q.filter(Document.category == category)

    docs = q.order_by(Document.upload_timestamp.desc()).all()

    # Apply expiry filter in Python for accurate property calculation
    if expiry_filter == "expiring_soon":
        docs = [d for d in docs if d.is_expiring_soon]
    elif expiry_filter == "expired":
        docs = [d for d in docs if d.is_expired]
    elif expiry_filter == "active":
        docs = [d for d in docs if not d.is_expired]

    # Manual pagination
    per_page = 10
    total = len(docs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_docs = docs[start:end]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return render_template(
        "documents/list.html",
        documents=paginated_docs,
        categories=DocumentCategory.ALL_CATEGORIES,
        current_category=category,
        current_query=query_str,
        current_expiry=expiry_filter,
        page=page,
        total_pages=total_pages,
        total_count=total,
    )


@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.EDITOR)
def upload():
    """Upload a new document."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", DocumentCategory.GENERAL)
        expiry_str = request.form.get("expiry_date", "").strip()

        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please choose a file to upload.", "danger")
            return redirect(request.url)

        expiry_date = None
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid expiry date format. Please use YYYY-MM-DD.", "danger")
                return redirect(request.url)

        doc, err_msg = upload_document(
            title=title,
            description=description,
            category=category,
            file_storage=file,
            owner=current_user,
            expiry_date=expiry_date,
            ip_address=request.remote_addr,
        )

        if doc:
            flash(f"Document '{doc.title}' uploaded successfully!", "success")
            return redirect(url_for("documents.detail", doc_id=doc.id))
        else:
            flash(err_msg, "danger")

    return render_template(
        "documents/upload.html",
        categories=DocumentCategory.ALL_CATEGORIES,
    )


@documents_bp.route("/<int:doc_id>")
@login_required
def detail(doc_id):
    """View document details and permissions."""
    doc = Document.query.get_or_404(doc_id)
    if not can_user_access_document(doc, current_user, operation="view"):
        log_event(
            action=AuditAction.ACCESS_DENIED,
            outcome=AuditOutcome.DENIED,
            actor_id=current_user.id,
            actor_username=current_user.username,
            document_id=doc_id,
            ip_address=request.remote_addr,
            details="View denied: user unauthorized",
        )
        abort(403)

    can_edit = can_user_access_document(doc, current_user, operation="edit")
    can_download = can_user_access_document(doc, current_user, operation="download")
    can_delete = can_user_access_document(doc, current_user, operation="delete")

    users = User.query.filter_by(is_active_account=True).all() if current_user.is_admin() else []

    return render_template(
        "documents/detail.html",
        document=doc,
        can_edit=can_edit,
        can_download=can_download,
        can_delete=can_delete,
        available_users=users,
        roles=UserRole.ALL_ROLES,
    )


@documents_bp.route("/<int:doc_id>/download")
@login_required
def download(doc_id):
    """Secure document download endpoint."""
    stream, doc, content_type, err = get_document_for_download(
        document_id=doc_id,
        user=current_user,
        ip_address=request.remote_addr,
    )

    if err:
        flash(err, "danger")
        if "Access denied" in err:
            abort(403)
        return redirect(url_for("documents.list_documents"))

    return send_file(
        stream,
        mimetype=content_type,
        as_attachment=True,
        download_name=doc.original_filename,
    )


@documents_bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
def edit(doc_id):
    """Edit document metadata."""
    doc = Document.query.get_or_404(doc_id)
    if not can_user_access_document(doc, current_user, operation="edit"):
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", doc.category)
        expiry_str = request.form.get("expiry_date", "").strip()

        expiry_date = None
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid expiry date format.", "danger")
                return redirect(request.url)

        success, msg = update_document_metadata(
            document_id=doc_id,
            title=title,
            description=description,
            category=category,
            expiry_date=expiry_date,
            user=current_user,
            ip_address=request.remote_addr,
        )

        if success:
            flash(msg, "success")
            return redirect(url_for("documents.detail", doc_id=doc.id))
        else:
            flash(msg, "danger")

    return render_template(
        "documents/edit.html",
        document=doc,
        categories=DocumentCategory.ALL_CATEGORIES,
    )


@documents_bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
@role_required(UserRole.ADMIN)
def delete(doc_id):
    """Delete document (admin-only)."""
    success, msg = delete_document(
        document_id=doc_id,
        user=current_user,
        ip_address=request.remote_addr,
    )
    if success:
        flash(msg, "success")
        return redirect(url_for("documents.list_documents"))
    else:
        flash(msg, "danger")
        return redirect(url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/<int:doc_id>/permissions", methods=["POST"])
@login_required
def manage_permissions(doc_id):
    """Grant permissions to another user or role (Admin or document owner only)."""
    doc = Document.query.get_or_404(doc_id)
    if not (current_user.is_admin() or doc.owner_id == current_user.id):
        abort(403)

    target_type = request.form.get("target_type")  # 'user' or 'role'
    can_edit = bool(request.form.get("can_edit"))
    can_download = bool(request.form.get("can_download", True))

    target_user_id = None
    target_role = None

    if target_type == "user":
        target_user_id = request.form.get("user_id", type=int)
        if not target_user_id:
            flash("Please choose a user to grant permissions.", "danger")
            return redirect(url_for("documents.detail", doc_id=doc.id))
    elif target_type == "role":
        target_role = request.form.get("role")
        if target_role not in UserRole.ALL_ROLES and target_role != "ALL":
            flash("Invalid role specified.", "danger")
            return redirect(url_for("documents.detail", doc_id=doc.id))

    perm = DocumentPermission(
        document_id=doc.id,
        user_id=target_user_id,
        role=target_role,
        can_download=can_download,
        can_edit=can_edit,
        granted_by_id=current_user.id,
    )
    db.session.add(perm)
    db.session.commit()

    log_event(
        action=AuditAction.PERMISSION_CHANGE,
        outcome=AuditOutcome.SUCCESS,
        actor_id=current_user.id,
        actor_username=current_user.username,
        document_id=doc.id,
        ip_address=request.remote_addr,
        details=f"Granted permission to {target_type}={target_user_id or target_role} (download={can_download}, edit={can_edit})",
    )

    flash("Permission granted successfully.", "success")
    return redirect(url_for("documents.detail", doc_id=doc.id))
