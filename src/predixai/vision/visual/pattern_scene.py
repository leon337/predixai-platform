"""Unified pattern scene metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern import Patterns
from predixai.vision.visual.pattern_registry import PatternRegistry


@dataclass(frozen=True)
class PatternScene:
    """Unified structural representation of detected patterns."""

    id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    market_structure: MarketStructure
    pattern_registry: PatternRegistry
    patterns: Patterns
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_count(self) -> int:
        return self.patterns.count

    @property
    def entity_count(self) -> int:
        return self.patterns.entity_count

    @property
    def region_count(self) -> int:
        return self.patterns.region_count

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "market_structure": self.market_structure.to_dict(),
            "pattern_registry": self.pattern_registry.to_dict(),
            "patterns": self.patterns.to_dict(),
            "pattern_count": self.pattern_count,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "metadata": dict(self.metadata),
        }
