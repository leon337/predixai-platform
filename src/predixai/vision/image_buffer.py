"""Image buffer metadata for the Vision Engine foundation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImageBuffer:
    """Metadata for a PNG loaded as bytes without pixel interpretation."""

    filename: str
    file_path: Path
    file_size: int
    sha256: str
    width: int
    height: int
    image_format: str
    loaded_at: str
    byte_size: int

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "filename": self.filename,
            "file_path": str(self.file_path),
            "file_size": self.file_size,
            "sha256": self.sha256,
            "width": self.width,
            "height": self.height,
            "image_format": self.image_format,
            "loaded_at": self.loaded_at,
            "byte_size": self.byte_size,
        }
