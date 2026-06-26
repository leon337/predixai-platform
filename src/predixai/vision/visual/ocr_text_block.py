"""Structured OCR text block metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OCRTextBlock:
    """One normalized block extracted from raw OCR text."""

    id: str
    index: int
    text: str
    confidence: float
    source_provider: str
    source_image_sha256: str
    source_image_path: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "index": self.index,
            "text": self.text,
            "confidence": self.confidence,
            "source_provider": self.source_provider,
            "source_image_sha256": self.source_image_sha256,
            "source_image_path": self.source_image_path,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }
