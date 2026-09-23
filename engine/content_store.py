import os
import gzip
import hashlib
from typing import Optional, Tuple

class ContentStore:
    """Content-addressed compressed storage for raw and rendered HTML."""
    def __init__(self, base_dir: str = "store"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, content_hash: str) -> str:
        prefix = content_hash[:2]
        rest = content_hash[2:]
        dir_path = os.path.join(self.base_dir, prefix)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{rest}.gz")

    def put(self, content: str) -> Tuple[str, str]:
        """Compresses and stores content by its SHA-256 hash.
        Returns: (content_hash, store_ref)
        """
        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = bytes(content)

        content_hash = hashlib.sha256(data).hexdigest()
        file_path = self._get_path(content_hash)
        
        # Deduplication: if already exists, don't re-compress
        if not os.path.exists(file_path):
            with gzip.open(file_path, "wb", compresslevel=6) as f:
                f.write(data)
                
        return content_hash, file_path

    def get(self, content_hash_or_path: str) -> Optional[str]:
        """Retrieves and decompresses content by SHA-256 hash or store path."""
        if os.path.exists(content_hash_or_path):
            file_path = content_hash_or_path
        else:
            file_path = self._get_path(content_hash_or_path)

        if not os.path.exists(file_path):
            return None

        try:
            with gzip.open(file_path, "rb") as f:
                return f.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    def exists(self, content_hash: str) -> bool:
        return os.path.exists(self._get_path(content_hash))
