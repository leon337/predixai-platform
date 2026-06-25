"""OCR foundation result metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRResult:
    """Technical OCR pipeline result without text extraction."""

    image_path: Path
    image_format: str
    file_size: int
    provider_name: str
    provider_loaded: bool
    pipeline_ready: bool
    text_extraction_enabled: bool
    created_at: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "image_path": str(self.image_path),
            "image_format": self.image_format,
            "file_size": self.file_size,
            "provider_name": self.provider_name,
            "provider_loaded": self.provider_loaded,
            "pipeline_ready": self.pipeline_ready,
            "text_extraction_enabled": self.text_extraction_enabled,
            "created_at": self.created_at,
        }
