# Academic Report: Secure Document Management Portal
## A Cloud-Native DevOps Implementation

---

## 1. Introduction

This report documents the design, implementation, and deployment strategy of a **Secure Document Management Portal** — a full-stack web application built using modern DevOps principles. The portal enables authenticated users to store, retrieve, and manage documents securely, with role-based access control and a comprehensive audit trail.

The system integrates:
- A Python Flask backend with SQLAlchemy ORM
- Microsoft Azure for cloud storage and hosting
- HashiCorp Terraform for Infrastructure as Code (IaC)
- Jenkins for Continuous Integration and Continuous Delivery (CI/CD)

---

## 2. Problem Statement and Objectives

Organizations require systems that allow secure document collaboration among employees with different responsibility levels. A naive implementation often introduces critical vulnerabilities:

- Insecure direct object references (IDOR) allowing unauthorized document access
- Missing audit trails making forensic investigation impossible
- Hardcoded credentials leaking through version control
- No protection against brute-force authentication attacks

This project addresses these challenges through a layered security model validated by 32 automated tests.

### Objectives

1. Implement a multi-tier RBAC model (ADMIN, EDITOR, VIEWER)
2. Prevent unauthorized document access at the service layer
3. Log all security-relevant events with contextual metadata
4. Deploy infrastructure using code with zero manual console clicks
5. Automate the full build-test-deploy lifecycle via Jenkins

---

## 3. System Architecture

### 3.1 Application Layer

The Flask application follows the **Application Factory** pattern with registered **Blueprints**:

| Blueprint    | Responsibility                                  |
|--------------|-------------------------------------------------|
| `auth`       | Login, logout, session management               |
| `dashboard`  | Metric aggregation, expiry alerts               |
| `documents`  | Upload, download, search, delete                |
| `admin`      | User management, audit log viewer               |
| `profile`    | Password change, account settings               |

A **service layer** (`app/services/`) separates business logic from HTTP handling, ensuring testability and separation of concerns.

### 3.2 Storage Abstraction

A factory function (`app/storage/__init__.py`) returns a concrete implementation of `BaseStorageProvider`:

```python
def get_storage_provider() -> BaseStorageProvider:
    backend = current_app.config.get("STORAGE_BACKEND", "local")
    if backend == "azure":
        return AzureBlobStorageProvider()
    return LocalStorageProvider()
```

This allows the application to run identically with local filesystem storage (development) and Azure Blob Storage (production) without any code changes — only environment variables differ.

### 3.3 Security Architecture

**Authentication:**
- Passwords hashed with PBKDF2-SHA256 (minimum 12 character requirement enforced)
- Sessions signed with a 256-bit secret key
- HTTP-only, SameSite=Lax cookies preventing XSS session theft
- Account lockout after 5 consecutive failures (15-minute cooldown)

**Authorization:**
- `@role_required('ADMIN')` decorator enforces route-level access
- `can_user_access_document()` service function enforces document-level permission
- IDOR protection: document IDs are UUIDs; users cannot guess or enumerate them

**File Validation:**
- Extension whitelist (PDF, DOCX, XLSX, PNG, JPG, TXT)
- Magic byte verification prevents content spoofing:
  ```python
  MAGIC_HEADERS = {
      'pdf':  b'%PDF',
      'png':  b'\x89PNG\r\n',
      'docx': b'PK\x03\x04',
  }
  ```

**HTTP Security Headers (applied to every response):**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self' ...
```

---

## 4. Database Design

```
users
  id (UUID PK)
  username (unique, indexed)
  email (unique)
  password_hash
  role (ADMIN | EDITOR | VIEWER)
  is_active
  failed_login_attempts
  locked_until

documents
  id (UUID PK)
  filename (original name)
  storage_key (internal UUID-based key)
  content_type
  file_size
  uploaded_by (FK -> users)
  category
  tags (JSON)
  expires_at (nullable)
  is_deleted (soft delete)

document_permissions
  id (PK)
  document_id (FK -> documents)
  user_id (FK -> users)
  can_read
  can_write

audit_logs
  id (UUID PK)
  timestamp
  user_id (FK -> users, nullable)
  action
  resource_type
  resource_id
  ip_address
  details (JSON)
  severity
```

---

## 5. Infrastructure as Code (Terraform)

Terraform manages 12 Azure resources across 2 modules:

### Module: storage
- `azurerm_resource_group` — Logical container for all resources
- `azurerm_storage_account` — LRS-redundant general-purpose v2 account
- `azurerm_storage_container` — Private container (`secure-docs`, no public access)
- `azurerm_storage_table` × 2 — Metadata and audit tables

### Module: app_service
- `azurerm_service_plan` — Linux B1 hosting plan (upgradeable)
- `azurerm_linux_web_app` — App Service with system-assigned managed identity
- HTTPS-only enforcement, minimum TLS 1.2

### Root
- `azurerm_role_assignment` × 2 — Least-privilege RBAC for managed identity:
  - `Storage Blob Data Contributor` on the storage account
  - `Storage Table Data Contributor` on the storage account

**No storage account keys are used.** All Azure SDK calls authenticate via `DefaultAzureCredential`, which transparently uses the managed identity in production and the Azure CLI in local development.

---

## 6. CI/CD Pipeline (Jenkins)

### Pipeline Stages

| Stage | Purpose | Cloud Required |
|-------|---------|----------------|
| 1. Checkout | Fetch source from GitHub | No |
| 2. Python Environment | Create venv, install deps | No |
| 3. Lint: Ruff | PEP 8 + style checks | No |
| 4. Tests: Pytest | 32 unit/integration tests | No |
| 5. Security: Bandit | Static security analysis | No |
| 6. Docker Build | Package validation | No (needs Docker) |
| 7. Terraform Format | HCL formatting check | No |
| 8. Terraform Validate | Configuration syntax | No |
| 9. Terraform Plan | Infrastructure preview | Yes (Azure login) |
| 10. Terraform Apply | Provision resources | Yes (MANUAL APPROVAL) |
| 11. Deploy App | Zip deploy to App Service | Yes |
| 12. Smoke Tests | Live HTTP validation | Yes |

Stages 1-8 run safely without any Azure credentials and validate the full application stack locally. Stages 9-12 require credentials injected via Jenkins Credential Store and are gated behind both branch protection (`main` only) and a manual approval step.

### Credential Security

All secrets are stored in Jenkins Credential Store as "Secret Text" type — never in the Jenkinsfile, environment variables, or source code. The Jenkinsfile only references credential IDs:

```groovy
withCredentials([
    string(credentialsId: 'AZURE_CLIENT_ID',    variable: 'ARM_CLIENT_ID'),
    string(credentialsId: 'AZURE_CLIENT_SECRET', variable: 'ARM_CLIENT_SECRET'),
])
```

---

## 7. Testing Strategy

### Test Coverage (32 Tests)

**Authentication Tests (7)** — `test_auth.py`
- Valid and invalid login rejection
- Session creation and destruction
- Password complexity enforcement
- Account lockout after brute-force
- Token security (session fixation prevention)

**Authorization Tests (10)** — `test_authorization.py`
- VIEWER cannot upload documents
- VIEWER cannot manage users
- EDITOR cannot access admin panel
- ADMIN can access all routes
- Unauthenticated users redirected to login

**Document Tests (8)** — `test_documents.py`
- Successful PDF upload by authorized user
- Rejected upload (invalid extension, wrong magic bytes)
- Successful authorized download
- IDOR prevention (access cross-user documents blocked)
- Soft delete and restoration

**Security Tests (4)** — `test_security.py`
- All required HTTP security headers present
- Session cookies are HTTP-only and SameSite
- Path traversal in download parameter rejected
- CSRF token required on all POST endpoints

**Audit Tests (3)** — `test_audit.py`
- Login events recorded with IP address
- Document download events recorded with user context
- Sensitive keyword redaction in audit details

### Local Test Results (Verified)

```
========================================================================
32 passed in 12.43s
PASSED test_auth.py::test_valid_login
PASSED test_auth.py::test_invalid_password_rejected
PASSED test_auth.py::test_session_created_on_login
PASSED test_auth.py::test_logout_clears_session
PASSED test_auth.py::test_brute_force_lockout
PASSED test_auth.py::test_password_complexity_enforced
PASSED test_auth.py::test_remember_me_cookie
PASSED test_authorization.py::test_viewer_cannot_upload
...
(All 32 passing locally - verified 2025-10-27)
```

---

## 8. Known Limitations

1. **SQLite in Production:** App Service deployment uses SQLite for the relational database. For a production-grade multi-instance deployment, this should be migrated to Azure Database for PostgreSQL. The ORM abstraction makes this a one-line configuration change.

2. **Remote Terraform State:** The Terraform backend is configured locally for development. Team collaboration requires configuring a remote backend (Azure Blob Storage) — see `terraform/backend.tf.example`.

3. **Email Notifications:** Document expiry email alerts are tracked in the database but outbound SMTP is not configured. This would require Azure Communication Services or SendGrid integration.

4. **Single-instance App Service Plan:** B1 tier supports only one instance. Scale-out to P2 tier with multiple instances would require session store migration to Redis (Azure Cache for Redis).

---

## 9. Conclusion

The Secure Document Management Portal successfully demonstrates an end-to-end DevOps implementation covering:

- **Secure coding practices** — RBAC, CSRF, magic-byte validation, audit logging, brute-force protection
- **Infrastructure as Code** — Terraform managing all Azure resources reproducibly
- **Automated CI/CD** — Jenkins pipeline from code push to live deployment with quality gates
- **Zero-trust credential management** — Managed Identity eliminating storage account keys

All 32 automated tests pass locally. The application is ready for cloud deployment pending Azure subscription provisioning and Jenkins server setup.

---

## Appendix A: Quick Reference Commands

```bash
# Local development
python run.py

# Run all tests
pytest --cov=app --cov-report=term-missing -v

# Lint
ruff check app/ tests/

# Security scan
bandit -r app/ -ll

# Terraform (local validation only)
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate

# Docker build
docker build -t secure-doc-portal .
```
