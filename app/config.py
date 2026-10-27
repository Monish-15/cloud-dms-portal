"""Application configuration module.

Supports Development, Testing, and Production environments.
Selects local storage or Azure Blob Storage based on STORAGE_BACKEND.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration with sensible defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-change-in-prod-8f92b71c")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads & Storage
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10MB default
    ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "txt"}
    LOCAL_UPLOAD_FOLDER = os.environ.get("LOCAL_UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")  # 'local' or 'azure'

    # Azure Configuration (used when STORAGE_BACKEND == 'azure')
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "secure-docs")
    AZURE_USE_MANAGED_IDENTITY = os.environ.get("AZURE_USE_MANAGED_IDENTITY", "true").lower() in ("true", "1", "yes")
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Enabled in Production
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Brute-force protection
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15

    # Initial Admin Seed (optional env vars)
    INITIAL_ADMIN_USERNAME = os.environ.get("INITIAL_ADMIN_USERNAME", "admin")
    INITIAL_ADMIN_EMAIL = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@portal.local")
    INITIAL_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD", "")


class DevelopmentConfig(Config):
    """Local development configuration."""

    DEBUG = True
    ENV = "development"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'dev_portal.db'}"
    )
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")


class TestingConfig(Config):
    """Testing configuration with in-memory SQLite and local storage."""

    TESTING = True
    DEBUG = False
    ENV = "testing"
    WTF_CSRF_ENABLED = False  # Disabled for unit tests to simplify payload testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_BACKEND = "local"
    LOCAL_UPLOAD_FOLDER = str(BASE_DIR / "tests" / "test_uploads")


class ProductionConfig(Config):
    """Production configuration for Azure deployment."""

    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "azure")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'prod_portal.db'}"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
