"""Registry of market hypotheses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_hypothesis import MarketHypotheses, MarketHypothesis


@dataclass(frozen=True)
class MarketHypothesisRegistry:
    id: str
    source_intelligence_context_id: str
    source_pattern_analysis_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    hypotheses: tuple[MarketHypothesis, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.hypotheses)

    @property
    def hypothesis_count(self) -> int:
        return self.count

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_intelligence_context_id": self.source_intelligence_context_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "hypothesis_count": self.hypothesis_count,
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "metadata": dict(self.metadata),
        }
