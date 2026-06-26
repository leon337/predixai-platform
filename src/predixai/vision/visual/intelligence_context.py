"""Intelligence context metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.visual_snapshot import VisualSnapshot


@dataclass(frozen=True)
class IntelligenceContext:
    id: str
    source_pattern_analysis_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    pattern_analysis: PatternAnalysis
    market_structure: MarketStructure
    visual_snapshot: VisualSnapshot
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def analysis_count(self) -> int:
        return self.pattern_analysis.pattern_count

    @property
    def entity_count(self) -> int:
        return self.market_structure.entity_count

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "pattern_analysis": self.pattern_analysis.to_dict(),
            "market_structure": self.market_structure.to_dict(),
            "visual_snapshot": self.visual_snapshot.to_dict(),
            "analysis_count": self.analysis_count,
            "entity_count": self.entity_count,
            "metadata": dict(self.metadata),
        }
