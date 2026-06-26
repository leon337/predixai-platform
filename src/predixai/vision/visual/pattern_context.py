"""Context metadata for pattern analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_scene import PatternScene
from predixai.vision.visual.visual_snapshot import VisualSnapshot


@dataclass(frozen=True)
class PatternContext:
    id: str
    source_pattern_scene_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    pattern_scene: PatternScene
    market_structure: MarketStructure
    visual_snapshot: VisualSnapshot
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_pattern_scene_id": self.source_pattern_scene_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "pattern_scene": self.pattern_scene.to_dict(),
            "market_structure": self.market_structure.to_dict(),
            "visual_snapshot": self.visual_snapshot.to_dict(),
            "metadata": dict(self.metadata),
        }
