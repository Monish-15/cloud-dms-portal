"""Storage provider factory."""

from app.storage.base import BaseStorageProvider
from app.storage.local import LocalStorageProvider
from app.storage.azure_blob import AzureBlobStorageProvider

_storage_provider = None


def init_storage(app) -> BaseStorageProvider:
    """Initialize storage provider based on application configuration."""
    global _storage_provider
    backend = app.config.get("STORAGE_BACKEND", "local").lower()

    if backend == "azure":
        _storage_provider = AzureBlobStorageProvider(
            account_name=app.config.get("AZURE_STORAGE_ACCOUNT_NAME", ""),
            container_name=app.config.get("AZURE_STORAGE_CONTAINER_NAME", "secure-docs"),
            use_managed_identity=app.config.get("AZURE_USE_MANAGED_IDENTITY", True),
            connection_string=app.config.get("AZURE_STORAGE_CONNECTION_STRING", ""),
        )
    else:
        _storage_provider = LocalStorageProvider(
            upload_folder=app.config.get("LOCAL_UPLOAD_FOLDER", "uploads")
        )

    return _storage_provider


def get_storage() -> BaseStorageProvider:
    """Get the current initialized storage provider."""
    global _storage_provider
    if _storage_provider is None:
        # Fallback to local default if called prior to app init
        _storage_provider = LocalStorageProvider(upload_folder="uploads")
    return _storage_provider
