"""Structured OCR result for a captured screen."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.region_text import RegionText


@dataclass(frozen=True)
class StructuredOCRResult:
    """Unified OCR structure with regions, text and metadata."""

    id: str
    source_frame: str
    created_at: str
    regions: tuple[RegionText, ...]
    combined_text: str
    average_confidence: float
    total_regions: int
    total_blocks: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "regions": [region.to_dict() for region in self.regions],
            "combined_text": self.combined_text,
            "average_confidence": self.average_confidence,
            "total_regions": self.total_regions,
            "total_blocks": self.total_blocks,
            "metadata": dict(self.metadata),
        }
