"""OCR cache storage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class OCRCache:
    """Persist OCR results by image SHA256."""

    def __init__(self, cache_directory: Path) -> None:
        self.cache_directory = cache_directory

    def compute_key(self, image_path: Path) -> str:
        """Compute the SHA256 cache key for one image."""
        digest = hashlib.sha256()
        with image_path.open("rb") as image_file:
            for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def load(self, cache_key: str) -> dict[str, object] | None:
        """Load a cached OCR result when it exists."""
        cache_path = self._cache_path(cache_key)
        if not cache_path.exists():
            return None

        with cache_path.open("r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)

        return data if isinstance(data, dict) else None

    def save(self, cache_key: str, data: dict[str, object]) -> Path:
        """Save one OCR result in the cache directory."""
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(cache_key)
        with cache_path.open("w", encoding="utf-8") as cache_file:
            json.dump(data, cache_file, ensure_ascii=False, indent=2)
            cache_file.write("\n")
        return cache_path

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_directory / f"{cache_key}.json"
