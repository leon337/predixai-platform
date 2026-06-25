"""Vision frame metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    """Metadata registered for one captured image file."""

    session_id: str
    timestamp: str
    filename: str
    width: int
    height: int
    file_size: int
    sha256: str
    image_format: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "sha256": self.sha256,
            "image_format": self.image_format,
        }
