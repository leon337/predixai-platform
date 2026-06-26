"""Build pattern analysis metadata."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.pattern_analysis import PatternAnalysis
from predixai.vision.visual.pattern_classifier_registry import PatternClassifierRegistry
from predixai.vision.visual.pattern_context import PatternContext
from predixai.vision.visual.pattern_scene import PatternScene


class PatternAnalysisBuilder:
    def build(
        self,
        pattern_scene: PatternScene,
        pattern_context: PatternContext,
        classification_registry: PatternClassifierRegistry,
    ) -> PatternAnalysis:
        created_at = datetime.now().astimezone().isoformat()
        classifications = tuple(
            classification.to_dict()
            for classification in classification_registry.classifications
        )
        contexts = (pattern_context.to_dict(),)
        analysis_results = (
            {
                "pattern_count": pattern_scene.pattern_count,
                "classification_count": classification_registry.count,
                "context_count": len(contexts),
                "source_pattern_scene_id": pattern_scene.id,
            },
        )
        return PatternAnalysis(
            id=f"pattern_analysis:{pattern_scene.source_market_structure_id}",
            source_pattern_scene_id=pattern_scene.id,
            source_market_structure_id=pattern_scene.source_market_structure_id,
            source_market_scene_id=pattern_scene.source_market_scene_id,
            source_visual_scene_id=pattern_scene.source_visual_scene_id,
            source_frame=pattern_scene.source_frame,
            created_at=created_at,
            pattern_scene=pattern_scene,
            classifications=classifications,
            contexts=contexts,
            analysis_results=analysis_results,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
