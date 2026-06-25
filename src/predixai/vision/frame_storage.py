"""Frame metadata storage helpers for the Vision Engine foundation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrameFileMetadata:
    """Technical file metadata used to create a Vision frame."""

    filename: str
    file_size: int
    sha256: str


class FrameStorage:
    """Read file metadata without storing or interpreting image content."""

    def load_metadata(self, file_path: Path) -> FrameFileMetadata:
        """Load file size, filename and SHA256 hash."""
        return FrameFileMetadata(
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            sha256=self.calculate_sha256(file_path),
        )

    def calculate_sha256(self, file_path: Path) -> str:
        """Calculate the SHA256 hash from file bytes."""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
