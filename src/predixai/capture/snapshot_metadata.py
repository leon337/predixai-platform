"""Manual snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SnapshotMetadata:
    """Metadata produced by one manual screen snapshot."""

    session_id: str
    captured_at: str
    resolution_width: int
    resolution_height: int
    file_path: Path
    file_size_bytes: int
    image_format: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "session_id": self.session_id,
            "captured_at": self.captured_at,
            "resolution": {
                "width": self.resolution_width,
                "height": self.resolution_height,
            },
            "file_path": str(self.file_path),
            "file_size_bytes": self.file_size_bytes,
            "image_format": self.image_format,
        }
