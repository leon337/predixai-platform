"""Image Loader foundation for PNG byte loading."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.image_loader_validator import ImageLoaderValidator


class ImageLoader:
    """Load PNG bytes and expose only technical metadata."""

    def __init__(self) -> None:
        self.validator = ImageLoaderValidator()

    def load(self, file_path: Path) -> ImageBuffer:
        """Load PNG file bytes without decoding or interpreting pixels."""
        image_bytes = self._load_bytes(file_path)
        validation = self.validator.validate(file_path, image_bytes)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return ImageBuffer(
            filename=file_path.name,
            file_path=file_path,
            file_size=file_path.stat().st_size,
            sha256=hashlib.sha256(image_bytes).hexdigest(),
            width=validation.width,
            height=validation.height,
            image_format=validation.image_format,
            loaded_at=datetime.now().astimezone().isoformat(),
            byte_size=len(image_bytes),
        )

    def _load_bytes(self, file_path: Path) -> bytes:
        if not file_path.exists() or not file_path.is_file():
            return b""
        return file_path.read_bytes()
