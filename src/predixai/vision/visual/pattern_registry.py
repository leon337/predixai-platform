"""Registry of structural patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.pattern import Pattern
from predixai.vision.visual.pattern_storage import PatternStorage


@dataclass(frozen=True)
class PatternRegistry:
    """Central registry of detected structural patterns."""

    id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    patterns: tuple[Pattern, ...]
    version: str = "1.0"
    enabled: bool = True
    profile_id: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)

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
            "id": self.id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "version": self.version,
            "enabled": self.enabled,
            "profile_id": self.profile_id,
            "count": self.count,
            "region_count": self.region_count,
            "entity_count": self.entity_count,
            "patterns": [pattern.to_dict() for pattern in self.patterns],
            "metadata": dict(self.metadata),
        }


class PatternSerializer:
    """Serialize pattern registries to plain dictionaries."""

    def serialize(self, registry: PatternRegistry) -> dict[str, object]:
        return registry.to_dict()
