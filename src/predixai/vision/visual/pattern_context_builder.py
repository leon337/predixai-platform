"""Build pattern context metadata."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern_scene import PatternScene
from predixai.vision.visual.pattern_context import PatternContext
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class PatternContextBuilder:
    def build(
        self,
        pattern_scene: PatternScene,
        market_structure: MarketStructure,
        visual_snapshot: VisualSnapshot,
    ) -> PatternContext:
        created_at = datetime.now().astimezone().isoformat()
        return PatternContext(
            id=f"pattern_context:{pattern_scene.source_market_structure_id}",
            source_pattern_scene_id=pattern_scene.id,
            source_market_structure_id=market_structure.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            created_at=created_at,
            pattern_scene=pattern_scene,
            market_structure=market_structure,
            visual_snapshot=visual_snapshot,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
