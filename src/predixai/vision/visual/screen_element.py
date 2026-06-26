"""Screen element metadata for visual understanding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScreenElement:
    """A deterministic visual element derived from structured screen data."""

    id: str
    element_type: str
    source: str
    source_region_id: str
    source_region_name: str
    x: int
    y: int
    width: int
    height: int
    text: str
    confidence: float
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "element_type": self.element_type,
            "source": self.source,
            "source_region_id": self.source_region_id,
            "source_region_name": self.source_region_name,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "text": self.text,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ScreenElements:
    """Collection of visual elements extracted from one visual snapshot."""

    source_snapshot_id: str
    source_frame: str
    created_at: str
    elements: tuple[ScreenElement, ...]

    @property
    def count(self) -> int:
        """Return the number of visual elements."""
        return len(self.elements)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_snapshot_id": self.source_snapshot_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "elements": [element.to_dict() for element in self.elements],
        }
