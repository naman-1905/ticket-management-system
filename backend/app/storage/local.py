import hashlib
import os
import uuid
from pathlib import Path

from ..config import settings


class LocalStorage:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, tenant_id: uuid.UUID, filename: str, data: bytes) -> tuple[str, str]:
        checksum = hashlib.sha256(data).hexdigest()
        key = f"{tenant_id}/{uuid.uuid4().hex}_{filename}"
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key, checksum

    def read(self, storage_key: str) -> bytes:
        return (self.base_dir / storage_key).read_bytes()
