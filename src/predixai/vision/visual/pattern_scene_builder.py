"""Build the unified pattern scene."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern import Patterns
from predixai.vision.visual.pattern_registry import PatternRegistry
from predixai.vision.visual.pattern_scene import PatternScene


class PatternSceneBuilder:
    """Consolidate market structure, pattern registry and pattern matches."""

    def build(
        self,
        market_structure: MarketStructure,
        pattern_registry: PatternRegistry,
        patterns: Patterns,
    ) -> PatternScene:
        created_at = datetime.now().astimezone().isoformat()
        return PatternScene(
            id=f"pattern_scene:{market_structure.frame_sha256}",
            source_market_structure_id=market_structure.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            created_at=created_at,
            market_structure=market_structure,
            pattern_registry=pattern_registry,
            patterns=patterns,
            metadata={
                "pattern_count": patterns.count,
                "entity_count": patterns.entity_count,
                "region_count": patterns.region_count,
                "structural_only": True,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
