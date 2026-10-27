# Secure Document Management Portal

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Flask 3.1](https://img.shields.io/badge/Flask-3.1-green)](https://flask.palletsprojects.com)
[![Terraform 1.10](https://img.shields.io/badge/Terraform-1.10-purple)](https://terraform.io)
[![Tests: 32 Passing](https://img.shields.io/badge/Tests-32%20Passing-brightgreen)](tests/)

A secure, production-ready document management application demonstrating cloud-native DevOps practices:
**Terraform IaC**, **Jenkins CI/CD**, and **Microsoft Azure** deployment.

---

## Abstract

This project implements a centralized document management portal where authenticated users upload,
organize, search, and retrieve documents according to their role-based permissions. The system uses
Azure Blob Storage for private document storage, Azure Table Storage for metadata, managed identity
for passwordless authentication, and a Jenkins CI/CD pipeline that validates, tests, and deploys
the application automatically.

---

## Features

- Secure authentication with bcrypt/PBKDF2 password hashing
- Three-tier RBAC: ADMIN, EDITOR, VIEWER
- Private Azure Blob Storage (no anonymous access)
- Document upload with magic-byte file type validation
- Secure authorized document streaming/download
- Comprehensive audit trail for all security events
- Document expiry tracking and dashboard alerts
- User management with account lockout protection
- 32 automated Pytest tests (authentication, authorization, documents, security, audit)
- Modular Terraform infrastructure (Resource Group, Storage, App Service, RBAC)
- Jenkins declarative CI/CD pipeline (12 stages)
- Docker multi-stage production build

---

## Repository Structure

```
secure-document-portal/
|-- app/
|   |-- __init__.py           # Application factory
|   |-- config.py             # Environment configuration
|   |-- extensions.py         # Flask extension instances
|   |-- models/               # SQLAlchemy ORM models
|   |   |-- user.py           # User model with RBAC
|   |   |-- document.py       # Document + Permission models
|   |   `-- audit.py          # Audit log model
|   |-- routes/               # Flask Blueprints
|   |   |-- auth.py           # Login / Logout
|   |   |-- dashboard.py      # Dashboard metrics
|   |   |-- documents.py      # Upload, download, search
|   |   |-- admin.py          # User management, audit logs
|   |   `-- profile.py        # User profile
|   |-- services/             # Business logic layer
|   |   |-- auth_service.py   # Authentication + brute force
|   |   |-- doc_service.py    # Document operations + AuthZ
|   |   `-- audit_service.py  # Audit event recording
|   |-- storage/              # Pluggable storage backends
|   |   |-- base.py           # Abstract interface
|   |   |-- local.py          # Local filesystem (dev/test)
|   |   `-- azure_blob.py     # Azure Blob Storage (prod)
|   `-- templates/            # Jinja2 + Bootstrap 5 UI
|-- tests/
|   |-- conftest.py           # Pytest fixtures
|   |-- test_auth.py          # Authentication tests
|   |-- test_authorization.py # RBAC tests
|   |-- test_documents.py     # Document handling tests
|   |-- test_security.py      # Headers, IDOR, path traversal
|   `-- test_audit.py         # Audit logging tests
|-- terraform/
|   |-- main.tf               # Root orchestration
|   |-- variables.tf          # Input variables
|   |-- outputs.tf            # Deployment outputs
|   |-- providers.tf          # Provider config
|   |-- versions.tf           # Version constraints
|   |-- modules/storage/      # Storage Account + Container
|   `-- modules/app_service/  # Linux App Service + Identity
|-- scripts/
|   `-- seed_dev_data.py      # Development demo data seeder
|-- Dockerfile                # Multi-stage production image
|-- Jenkinsfile               # 12-stage CI/CD pipeline
|-- requirements.txt          # Production dependencies
|-- requirements-dev.txt      # Development/test dependencies
|-- pytest.ini                # Pytest configuration
|-- pyproject.toml            # Ruff + Bandit configuration
|-- run.py                    # Application entrypoint
`-- .env.example              # Environment variable template
```

---

## Technology Stack

| Layer           | Technology                           |
|-----------------|--------------------------------------|
| Backend         | Python 3.11, Flask 3.1               |
| Auth            | Flask-Login, Werkzeug password hash  |
| ORM             | Flask-SQLAlchemy 3.1, SQLAlchemy 2.0 |
| CSRF            | Flask-WTF 1.2                        |
| Frontend        | Bootstrap 5.3, Jinja2, Bootstrap Icons |
| Local Storage   | SQLite (dev), Local filesystem       |
| Cloud Storage   | Azure Blob Storage (private)          |
| Cloud Metadata  | Azure Table Storage                   |
| Auth (Cloud)    | Azure Managed Identity (Entra ID)     |
| IaC             | Terraform 1.10 + AzureRM 3.110       |
| CI/CD           | Jenkins, GitHub                       |
| Testing         | Pytest 8.3, pytest-cov               |
| Linting         | Ruff 0.9                             |
| Security Scan   | Bandit 1.8                           |
| Containers      | Docker                               |

---

## Prerequisites

- Python 3.10+
- Git
- Docker (for container build)
- Terraform 1.5+ (provided in `bin/`)
- Azure CLI (for deployment only — not required locally)
- Jenkins (for CI/CD — not required for local development)

---

## Local Installation

```bash
# 1. Clone the repository
git clone <your-github-repo-url>
cd secure-document-portal

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Copy and configure environment variables
copy .env.example .env

# 5. Seed development database with demo data
python scripts/seed_dev_data.py

# 6. Run the application
python run.py
# Open: http://localhost:5000
```

### Demo Credentials (Local Development Only)

| Role   | Username | Password        |
|--------|----------|-----------------|
| ADMIN  | admin    | AdminPass123!   |
| EDITOR | editor   | EditorPass123!  |
| VIEWER | viewer   | ViewerPass123!  |

**These credentials exist only in the local SQLite database and are NOT used in production.**

---

## Environment Configuration

Key variables (see `.env.example` for complete list):

| Variable                    | Description                        | Default       |
|-----------------------------|------------------------------------|---------------|
| `FLASK_ENV`                 | App mode (development/production)  | development   |
| `SECRET_KEY`                | Session signing key                | dev-key       |
| `STORAGE_BACKEND`           | `local` or `azure`                 | local         |
| `AZURE_STORAGE_ACCOUNT_NAME`| Storage account name               | (required)    |
| `AZURE_USE_MANAGED_IDENTITY`| Use Managed Identity in Azure      | true          |
| `DATABASE_URL`              | SQLAlchemy database URI            | SQLite        |

---

## Running Tests

```bash
# Full test suite with coverage
.venv\Scripts\pytest --cov=app --cov-report=term-missing -v

# Results summary (32 tests):
# test_auth.py         ::  7 tests  - Authentication & session security
# test_authorization.py:: 10 tests  - RBAC enforcement
# test_documents.py    ::  8 tests  - Upload, download, IDOR prevention
# test_security.py     ::  4 tests  - HTTP headers, cookies, path traversal
# test_audit.py        ::  3 tests  - Audit log creation and redaction
```

---

## Terraform Configuration

> **WARNING**: Terraform commands create REAL Azure resources that incur billing costs.
> Only run `terraform apply` after you have reviewed the plan and have an active subscription.

```bash
# 1. Navigate to terraform directory
cd terraform

# 2. Format check (safe - no cloud calls)
terraform fmt -check -recursive

# 3. Initialize (downloads providers - safe, no auth needed)
terraform init -backend=false

# 4. Validate (safe - no cloud calls)
terraform validate

# 5. Configure variables
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 6. Plan (preview - requires Azure authentication)
az login
terraform plan -out=tfplan.binary

# 7. Apply (CREATES RESOURCES - requires approval)
# Review the plan carefully before applying!
terraform apply tfplan.binary

# 8. View outputs
terraform output

# Cleanup (DESTROYS ALL RESOURCES - irreversible!)
# terraform destroy
```

---

## Azure Authentication Steps (Required Before Deployment)

**⚠️ DO NOT attempt until you have an active Azure subscription.**

```bash
# Step 1: Login to Azure
az login

# Step 2: Set subscription
az account set --subscription "<your-subscription-id>"

# Step 3: Create Jenkins service principal (least-privilege deployment identity)
az ad sp create-for-rbac \
  --name "sp-jenkins-docportal-deploy" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id>

# Step 4: Store SP credentials in Jenkins Credential Store (not in code!)
# AZURE_CLIENT_ID     -> Application (client) ID
# AZURE_CLIENT_SECRET -> Client secret value
# AZURE_TENANT_ID     -> Directory (tenant) ID
# AZURE_SUBSCRIPTION_ID -> Subscription ID
```

---

## Jenkins Pipeline Setup

**Requires a running Jenkins server with:**
- Git plugin
- Pipeline plugin
- HTML Publisher plugin (for coverage reports)
- AnsiColor plugin

```
1. New Item -> Pipeline
2. Pipeline Definition: "Pipeline script from SCM"
3. SCM: Git, Repository URL: <your GitHub repo>
4. Branch: */main
5. Script Path: Jenkinsfile
6. Add Credentials (see Azure Authentication section)
7. Build Now (runs locally safe stages; cloud stages gated by branch=main + TF_AUTO_APPLY=true)
```

---

## Checklist: Connect GitHub, Jenkins, and Azure

### Step 1 — GitHub Setup
- [ ] Create a GitHub account at github.com
- [ ] Create a new repository (e.g., `secure-document-portal`)
- [ ] Initialize git in this workspace: `git init && git remote add origin <url>`
- [ ] Push code: `git add -A && git commit -m "Initial commit" && git push -u origin main`
- [ ] Generate a GitHub Personal Access Token (Settings > Developer Settings > PAT)

### Step 2 — Jenkins Setup
- [ ] Install Jenkins (local: https://www.jenkins.io/download/ or Docker: `docker run -p 8080:8080 jenkins/jenkins:lts`)
- [ ] Complete Jenkins setup wizard and install suggested plugins
- [ ] Install additional plugins: AnsiColor, HTML Publisher, Pipeline
- [ ] Add GitHub credentials in Jenkins: Manage Jenkins > Credentials > Global
- [ ] Create a Pipeline job pointing to your GitHub repository
- [ ] Set branch to `*/main` and Script Path to `Jenkinsfile`

### Step 3 — Azure Setup
- [ ] Activate Azure subscription (free trial at portal.azure.com or student credit)
- [ ] Install Azure CLI locally: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
- [ ] Run `az login` and verify your subscription with `az account show`
- [ ] Create Jenkins service principal (see Azure Authentication section above)
- [ ] Store all 5 credentials in Jenkins Credential Store

### Step 4 — Infrastructure Provisioning (Approval Required)
- [ ] Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`
- [ ] Fill in your prefix, region, and secret key values
- [ ] Run `terraform plan` and review resources (14 resources expected)
- [ ] Tell me: "I approve running terraform apply" — I will guide you through it
- [ ] Set Jenkins env variable `TF_AUTO_APPLY=true` to enable cloud pipeline stages

### Step 5 — Post-Deployment Verification
- [ ] Run `terraform output app_service_url` to get the live URL
- [ ] Run `flask seed-admin` CLI command against the deployed App Service
- [ ] Test login, document upload, and download on the live URL
- [ ] Confirm documents are stored in Azure Blob Storage (Azure Portal > Storage Account)
- [ ] Confirm managed identity RBAC assignments in Azure Portal > IAM

---

## Security Considerations

- All passwords hashed with PBKDF2-SHA256 (Werkzeug)
- CSRF protection on all POST forms (Flask-WTF)
- HTTP-only, SameSite=Lax session cookies
- Security headers on every response (X-Frame-Options, X-Content-Type-Options, etc.)
- Server-side RBAC enforcement (not just UI hiding)
- File uploads validated by magic bytes, not just extension
- Storage IDs are UUIDs (not user-controlled filenames)
- No storage account keys in source code
- Managed Identity for Azure authentication (no long-lived secrets)
- Least-privilege Azure RBAC (Storage Blob Data Contributor only)
- Audit log redaction of sensitive keyword content
- Brute-force lockout after 5 failed login attempts

---

## Resource Cleanup

After project evaluation, destroy all Azure resources to prevent ongoing charges:

```bash
cd terraform
terraform destroy
# Type 'yes' when prompted
# This PERMANENTLY deletes all documents, storage accounts, and App Service
```

---

## Limitations

1. **Local dev uses SQLite** — Azure Table Storage adapter not yet implemented; production metadata uses SQLite on App Service (acceptable for academic scope)
2. **Email notifications** not implemented (optional enhancement)
3. **Bandit** has partial Python 3.14 compatibility issues (internal AST errors); core security scan runs but some checks skipped — use Python 3.11 for CI/CD
4. **Remote Terraform state** must be bootstrapped separately before team use
5. **GitHub webhook** to Jenkins requires a publicly accessible Jenkins URL (use ngrok for local Jenkins)

---

## License

MIT License — For academic and educational use.