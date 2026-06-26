"""Build intelligence context metadata."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.intelligence_context import IntelligenceContext
from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class IntelligenceContextBuilder:
    def build(
        self,
        pattern_analysis: PatternAnalysis,
        market_structure: MarketStructure,
        visual_snapshot: VisualSnapshot,
    ) -> IntelligenceContext:
        created_at = datetime.now().astimezone().isoformat()
        return IntelligenceContext(
            id=f"intelligence_context:{pattern_analysis.source_market_structure_id}",
            source_pattern_analysis_id=pattern_analysis.id,
            source_market_structure_id=market_structure.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            created_at=created_at,
            pattern_analysis=pattern_analysis,
            market_structure=market_structure,
            visual_snapshot=visual_snapshot,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
