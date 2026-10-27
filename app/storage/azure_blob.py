"""Azure Blob Storage provider using Managed Identity or Connection String."""

import io
import logging
from typing import BinaryIO, Tuple
from app.storage.base import BaseStorageProvider

logger = logging.getLogger(__name__)


class AzureBlobStorageProvider(BaseStorageProvider):
    """Stores files privately in Azure Blob Storage with zero anonymous access."""

    def __init__(
        self,
        account_name: str,
        container_name: str,
        use_managed_identity: bool = True,
        connection_string: str = "",
    ):
        self.account_name = account_name
        self.container_name = container_name
        self.use_managed_identity = use_managed_identity
        self.connection_string = connection_string
        self._client = None
        self._container_client = None

    def _get_client(self):
        """Lazy initialization of Azure BlobServiceClient."""
        if self._client is not None:
            return self._client

        from azure.storage.blob import BlobServiceClient

        if self.connection_string:
            logger.info("Initializing Azure Blob Storage via connection string.")
            self._client = BlobServiceClient.from_connection_string(self.connection_string)
        elif self.use_managed_identity and self.account_name:
            from azure.identity import DefaultAzureCredential

            account_url = f"https://{self.account_name}.blob.core.windows.net"
            logger.info(
                "Initializing Azure Blob Storage via Managed Identity (DefaultAzureCredential) for %s",
                account_url,
            )
            credential = DefaultAzureCredential()
            self._client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            raise ValueError(
                "Azure Blob Storage configuration missing: provide account_name with Managed Identity or connection_string."
            )

        self._container_client = self._client.get_container_client(self.container_name)
        return self._client

    def _get_container(self):
        self._get_client()
        return self._container_client

    def save_file(
        self, storage_id: str, file_stream: BinaryIO, filename: str, content_type: str
    ) -> int:
        from azure.storage.blob import ContentSettings

        container = self._get_container()
        blob_client = container.get_blob_client(storage_id)

        data = file_stream.read()
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return len(data)

    def get_file_stream(self, storage_id: str) -> Tuple[BinaryIO, str]:
        from azure.core.exceptions import ResourceNotFoundError

        container = self._get_container()
        blob_client = container.get_blob_client(storage_id)

        try:
            properties = blob_client.get_blob_properties()
            content_type = properties.content_settings.content_type or "application/octet-stream"
            download_stream = blob_client.download_blob()
            stream = io.BytesIO(download_stream.readall())
            return stream, content_type
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found for storage_id: {storage_id}")

    def delete_file(self, storage_id: str) -> bool:
        from azure.core.exceptions import ResourceNotFoundError

        container = self._get_container()
        blob_client = container.get_blob_client(storage_id)
        try:
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False

    def file_exists(self, storage_id: str) -> bool:
        from azure.core.exceptions import ResourceNotFoundError

        container = self._get_container()
        blob_client = container.get_blob_client(storage_id)
        try:
            return blob_client.exists()
        except ResourceNotFoundError:
            return False
