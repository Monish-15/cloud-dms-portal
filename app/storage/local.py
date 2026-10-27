"""Local filesystem storage provider for development and testing."""

import mimetypes
import os
from pathlib import Path
from typing import BinaryIO, Tuple
from app.storage.base import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    """Stores files on the local filesystem."""

    def __init__(self, upload_folder: str):
        self.upload_folder = Path(upload_folder).resolve()
        self.upload_folder.mkdir(parents=True, exist_ok=True)

    def _get_path(self, storage_id: str) -> Path:
        """Resolve storage path safely, preventing directory traversal."""
        safe_name = os.path.basename(storage_id)
        return self.upload_folder / safe_name

    def save_file(
        self, storage_id: str, file_stream: BinaryIO, filename: str, content_type: str
    ) -> int:
        target_path = self._get_path(storage_id)
        bytes_written = 0
        with open(target_path, "wb") as f:
            while chunk := file_stream.read(64 * 1024):
                f.write(chunk)
                bytes_written += len(chunk)
        return bytes_written

    def get_file_stream(self, storage_id: str) -> Tuple[BinaryIO, str]:
        target_path = self._get_path(storage_id)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found for storage_id: {storage_id}")

        content_type, _ = mimetypes.guess_type(target_path)
        if not content_type:
            content_type = "application/octet-stream"

        stream = open(target_path, "rb")
        return stream, content_type

    def delete_file(self, storage_id: str) -> bool:
        target_path = self._get_path(storage_id)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def file_exists(self, storage_id: str) -> bool:
        return self._get_path(storage_id).exists()
