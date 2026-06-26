"""Semantic element metadata for deterministic interface semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticElement:
    """A semantic entity derived from a visual scene without AI."""

    id: str
    source_scene_id: str
    source_object_id: str
    source_element_id: str
    stable_key: str
    semantic_type: str
    region_id: str
    region_name: str
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_scene_id": self.source_scene_id,
            "source_object_id": self.source_object_id,
            "source_element_id": self.source_element_id,
            "stable_key": self.stable_key,
            "semantic_type": self.semantic_type,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "text": self.text,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "confidence": self.confidence,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticElements:
    """Collection of semantic elements derived from one visual scene."""

    source_scene_id: str
    source_frame: str
    created_at: str
    elements: tuple[SemanticElement, ...]

    @property
    def count(self) -> int:
        """Return the number of semantic elements."""
        return len(self.elements)

    @property
    def region_count(self) -> int:
        """Return the number of regions represented by semantic elements."""
        return len({element.region_id for element in self.elements})

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_scene_id": self.source_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "region_count": self.region_count,
            "elements": [element.to_dict() for element in self.elements],
        }
