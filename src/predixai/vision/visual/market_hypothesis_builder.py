"""Build structural market hypotheses."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.intelligence_context import IntelligenceContext
from predixai.vision.visual.market_hypothesis import MarketHypotheses, MarketHypothesis
from predixai.vision.visual.hypothesis_score import HypothesisScore


class MarketHypothesisBuilder:
    def build(
        self,
        intelligence_context: IntelligenceContext,
        score: HypothesisScore,
    ) -> MarketHypotheses:
        created_at = datetime.now().astimezone().isoformat()
        hypotheses = tuple(
            self._build_hypothesis(intelligence_context, score, created_at)
            for _ in range(1)
        )
        return MarketHypotheses(
            source_intelligence_context_id=intelligence_context.id,
            source_pattern_analysis_id=intelligence_context.source_pattern_analysis_id,
            source_market_structure_id=intelligence_context.source_market_structure_id,
            source_market_scene_id=intelligence_context.source_market_scene_id,
            source_visual_scene_id=intelligence_context.source_visual_scene_id,
            source_frame=intelligence_context.source_frame,
            created_at=created_at,
            hypotheses=hypotheses,
        )

    def _build_hypothesis(
        self,
        intelligence_context: IntelligenceContext,
        score: HypothesisScore,
        created_at: str,
    ) -> MarketHypothesis:
        return MarketHypothesis(
            id=f"market_hypothesis:{intelligence_context.source_pattern_analysis_id}",
            source_intelligence_context_id=intelligence_context.id,
            source_pattern_analysis_id=intelligence_context.source_pattern_analysis_id,
            source_market_structure_id=intelligence_context.source_market_structure_id,
            source_market_scene_id=intelligence_context.source_market_scene_id,
            source_visual_scene_id=intelligence_context.source_visual_scene_id,
            source_frame=intelligence_context.source_frame,
            created_at=created_at,
            hypothesis_type="STRUCTURAL_HYPOTHESIS",
            description="Structural hypothesis derived from analysis context without AI or decision-making.",
            confidence=score.value,
            intelligence_context=intelligence_context,
            score=score.to_dict(),
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
