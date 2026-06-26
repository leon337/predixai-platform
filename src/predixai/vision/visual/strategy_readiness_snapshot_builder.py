"""Build strategy readiness snapshots."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot
from predixai.vision.visual.market_hypothesis import MarketHypotheses
from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.signal import Signals
from predixai.vision.visual.signal_score import SignalScore
from predixai.vision.visual.strategy_readiness_snapshot import StrategyReadinessSnapshot


class StrategyReadinessSnapshotBuilder:
    def build(
        self,
        pattern_analysis: PatternAnalysis,
        intelligence_snapshot: IntelligenceSnapshot,
        market_hypotheses: MarketHypotheses,
        signals: Signals,
        scores: tuple[SignalScore, ...],
    ) -> StrategyReadinessSnapshot:
        created_at = datetime.now().astimezone().isoformat()
        return StrategyReadinessSnapshot(
            id=f"strategy_readiness_snapshot:{intelligence_snapshot.id}",
            source_intelligence_snapshot_id=intelligence_snapshot.id,
            source_pattern_analysis_id=pattern_analysis.id,
            source_market_structure_id=pattern_analysis.source_market_structure_id,
            source_market_scene_id=pattern_analysis.source_market_scene_id,
            source_visual_scene_id=pattern_analysis.source_visual_scene_id,
            source_frame=pattern_analysis.source_frame,
            created_at=created_at,
            pattern_analysis=pattern_analysis,
            intelligence_snapshot=intelligence_snapshot,
            market_hypotheses=market_hypotheses,
            signals=signals,
            scores=scores,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
