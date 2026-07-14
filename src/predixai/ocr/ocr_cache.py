"""OCR cache storage."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Mapping


class OCRCache:
    def __init__(self, cache_directory: Path) -> None:
        self.cache_directory = cache_directory

    @staticmethod
    def compute_image_sha256(image_path: Path) -> str:
        digest = hashlib.sha256()
        with image_path.open("rb") as image_file:
            for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def compute_key(self, image_path: Path, *, namespace: Mapping[str, object] | None = None) -> str:
        digest = hashlib.sha256()
        digest.update(self.compute_image_sha256(image_path).encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(dict(namespace or {}), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return digest.hexdigest()

    def load(self, cache_key: str) -> dict[str, object] | None:
        try:
            cache_path = self._cache_path(cache_key)
            if not cache_path.is_file() or cache_path.is_symlink():
                return None
            with cache_path.open("r", encoding="utf-8") as cache_file:
                data = json.load(cache_file)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def save(self, cache_key: str, data: dict[str, object]) -> Path:
        self.cache_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.cache_directory, 0o700)
        cache_path = self._cache_path(cache_key)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{cache_key}.", suffix=".tmp", dir=self.cache_directory)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
                descriptor = -1
                json.dump(data, cache_file, ensure_ascii=False, indent=2)
                cache_file.write("\n")
                cache_file.flush()
                os.fsync(cache_file.fileno())
            os.replace(temporary_path, cache_path)
            os.chmod(cache_path, 0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary_path.unlink(missing_ok=True)
        return cache_path

    def _cache_path(self, cache_key: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}", cache_key) is None:
            raise ValueError("invalid OCR cache key")
        return self.cache_directory / f"{cache_key}.json"
