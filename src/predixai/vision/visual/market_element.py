"""Market interface element metadata derived from semantic scenes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MarketElement:
    """A structural market interface element without operational meaning."""

    id: str
    source_semantic_scene_id: str
    source_semantic_element_id: str
    source_object_id: str
    stable_key: str
    market_type: str
    region_id: str
    region_name: str
    text: str
    labels: tuple[str, ...]
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
            "source_semantic_scene_id": self.source_semantic_scene_id,
            "source_semantic_element_id": self.source_semantic_element_id,
            "source_object_id": self.source_object_id,
            "stable_key": self.stable_key,
            "market_type": self.market_type,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "text": self.text,
            "labels": list(self.labels),
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
class MarketElements:
    """Collection of market elements derived from one semantic scene."""

    source_semantic_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    elements: tuple[MarketElement, ...]

    @property
    def count(self) -> int:
        """Return the number of market elements."""
        return len(self.elements)

    @property
    def region_count(self) -> int:
        """Return the number of regions represented by market elements."""
        return len({element.region_id for element in self.elements})

    @property
    def entity_count(self) -> int:
        """Return the number of structural market entities."""
        return self.count

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_semantic_scene_id": self.source_semantic_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "region_count": self.region_count,
            "entity_count": self.entity_count,
            "elements": [element.to_dict() for element in self.elements],
        }
