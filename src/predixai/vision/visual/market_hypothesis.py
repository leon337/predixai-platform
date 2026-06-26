"""Market hypothesis metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.intelligence_context import IntelligenceContext


@dataclass(frozen=True)
class MarketHypothesis:
    id: str
    source_intelligence_context_id: str
    source_pattern_analysis_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    hypothesis_type: str
    description: str
    confidence: float
    intelligence_context: IntelligenceContext
    score: dict[str, object]
    metadata: dict[str, Any] = field(default_factory=dict)

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
            "hypothesis_type": self.hypothesis_type,
            "description": self.description,
            "confidence": self.confidence,
            "intelligence_context": self.intelligence_context.to_dict(),
            "score": dict(self.score),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class MarketHypotheses:
    source_intelligence_context_id: str
    source_pattern_analysis_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    hypotheses: tuple[MarketHypothesis, ...]

    @property
    def count(self) -> int:
        return len(self.hypotheses)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_intelligence_context_id": self.source_intelligence_context_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "hypotheses": [item.to_dict() for item in self.hypotheses],
        }
