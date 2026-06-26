"""Pattern metadata derived from market structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Pattern:
    """Structural market pattern without interpretation or decisions."""

    id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    stable_key: str
    pattern_type: str
    name: str
    description: str
    region_id: str
    region_name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    entity_ids: tuple[str, ...]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "stable_key": self.stable_key,
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "confidence": self.confidence,
            "entity_ids": list(self.entity_ids),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Patterns:
    """Collection of structural patterns from one market structure."""

    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    patterns: tuple[Pattern, ...]

    @property
    def count(self) -> int:
        return len(self.patterns)

    @property
    def region_count(self) -> int:
        return len({pattern.region_id for pattern in self.patterns})

    @property
    def entity_count(self) -> int:
        return len({entity_id for pattern in self.patterns for entity_id in pattern.entity_ids})

    def to_dict(self) -> dict[str, object]:
        return {
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "region_count": self.region_count,
            "entity_count": self.entity_count,
            "patterns": [pattern.to_dict() for pattern in self.patterns],
        }
