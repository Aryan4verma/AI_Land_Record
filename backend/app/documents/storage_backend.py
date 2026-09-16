"""Binary object storage. The bucket is private; only the backend
service_role key ever touches it — credentials never leave the server.
"""
from typing import Any, Protocol

from fastapi import Request

from ..config import get_settings
from ..database import require_db


class StorageBackend(Protocol):
    def upload(self, path: str, data: bytes, content_type: str) -> None: ...
    def remove(self, path: str) -> None: ...
    def download(self, path: str) -> bytes: ...


class SupabaseStorageBackend:
    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        self.client.storage.from_(self.bucket).upload(
            path, data, {"content-type": content_type, "upsert": "false"}
        )

    def remove(self, path: str) -> None:
        self.client.storage.from_(self.bucket).remove([path])

    def download(self, path: str) -> bytes:
        return self.client.storage.from_(self.bucket).download(path)


def get_storage_backend(request: Request) -> StorageBackend:
    return SupabaseStorageBackend(require_db(request), get_settings().storage_bucket)
