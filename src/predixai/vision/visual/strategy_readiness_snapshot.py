"""Strategy readiness snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot
from predixai.vision.visual.market_hypothesis import MarketHypotheses
from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.signal import Signals
from predixai.vision.visual.signal_score import SignalScore


@dataclass(frozen=True)
class StrategyReadinessSnapshot:
    id: str
    source_intelligence_snapshot_id: str
    source_pattern_analysis_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    pattern_analysis: PatternAnalysis
    intelligence_snapshot: IntelligenceSnapshot
    market_hypotheses: MarketHypotheses
    signals: Signals
    scores: tuple[SignalScore, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def signal_count(self) -> int:
        return self.signals.count

    @property
    def hypothesis_count(self) -> int:
        return self.market_hypotheses.count

    @property
    def analysis_count(self) -> int:
        return self.pattern_analysis.pattern_count

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_intelligence_snapshot_id": self.source_intelligence_snapshot_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "pattern_analysis": self.pattern_analysis.to_dict(),
            "intelligence_snapshot": self.intelligence_snapshot.to_dict(),
            "market_hypotheses": self.market_hypotheses.to_dict(),
            "signals": self.signals.to_dict(),
            "scores": [score.to_dict() for score in self.scores],
            "signal_count": self.signal_count,
            "hypothesis_count": self.hypothesis_count,
            "analysis_count": self.analysis_count,
            "metadata": dict(self.metadata),
        }
