"""Build intelligence snapshots."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.intelligence_context import IntelligenceContext
from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot
from predixai.vision.visual.market_hypothesis import MarketHypotheses
from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_analysis import PatternAnalysis


class IntelligenceSnapshotBuilder:
    def build(
        self,
        market_structure: MarketStructure,
        pattern_analysis: PatternAnalysis,
        intelligence_context: IntelligenceContext,
        market_hypotheses: MarketHypotheses,
    ) -> IntelligenceSnapshot:
        created_at = datetime.now().astimezone().isoformat()
        return IntelligenceSnapshot(
            id=f"intelligence_snapshot:{market_structure.frame_sha256}",
            source_market_structure_id=market_structure.id,
            source_pattern_analysis_id=pattern_analysis.id,
            source_intelligence_context_id=intelligence_context.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            created_at=created_at,
            market_structure=market_structure,
            pattern_analysis=pattern_analysis,
            intelligence_context=intelligence_context,
            market_hypotheses=market_hypotheses,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
