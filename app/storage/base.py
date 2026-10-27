"""Base abstract storage provider interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple


class BaseStorageProvider(ABC):
    """Abstract storage provider for local and cloud file operations."""

    @abstractmethod
    def save_file(
        self, storage_id: str, file_stream: BinaryIO, filename: str, content_type: str
    ) -> int:
        """Save a file stream using its unique storage_id.

        Returns total bytes written.
        """
        pass

    @abstractmethod
    def get_file_stream(self, storage_id: str) -> Tuple[BinaryIO, str]:
        """Retrieve a file stream and content type by storage_id.

        Returns (stream, content_type).
        """
        pass

    @abstractmethod
    def delete_file(self, storage_id: str) -> bool:
        """Delete a file by storage_id."""
        pass

    @abstractmethod
    def file_exists(self, storage_id: str) -> bool:
        """Check if file exists in the storage provider."""
        pass
