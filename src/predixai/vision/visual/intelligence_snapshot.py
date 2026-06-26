"""Intelligence snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.intelligence_context import IntelligenceContext
from predixai.vision.visual.market_hypothesis import MarketHypotheses
from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_analysis import PatternAnalysis


@dataclass(frozen=True)
class IntelligenceSnapshot:
    id: str
    source_market_structure_id: str
    source_pattern_analysis_id: str
    source_intelligence_context_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    market_structure: MarketStructure
    pattern_analysis: PatternAnalysis
    intelligence_context: IntelligenceContext
    market_hypotheses: MarketHypotheses
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hypothesis_count(self) -> int:
        return self.market_hypotheses.count

    @property
    def analysis_count(self) -> int:
        return self.pattern_analysis.pattern_count

    @property
    def entity_count(self) -> int:
        return self.market_structure.entity_count

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_intelligence_context_id": self.source_intelligence_context_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "market_structure": self.market_structure.to_dict(),
            "pattern_analysis": self.pattern_analysis.to_dict(),
            "intelligence_context": self.intelligence_context.to_dict(),
            "market_hypotheses": self.market_hypotheses.to_dict(),
            "hypothesis_count": self.hypothesis_count,
            "analysis_count": self.analysis_count,
            "entity_count": self.entity_count,
            "metadata": dict(self.metadata),
        }
