"""Build a unified structural market interface scene."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_element import MarketElements
from predixai.vision.visual.market_scene import MarketScene
from predixai.vision.visual.price_region_mapper import PriceRegionMapping
from predixai.vision.visual.semantic_scene import SemanticScene
from predixai.vision.visual.time_region_mapper import TimeRegionMapping
from predixai.vision.visual.visual_scene import VisualScene


class MarketSceneBuilder:
    """Consolidate visual, semantic and market structures."""

    def build(
        self,
        visual_scene: VisualScene,
        semantic_scene: SemanticScene,
        market_elements: MarketElements,
        price_regions: PriceRegionMapping,
        time_regions: TimeRegionMapping,
    ) -> MarketScene:
        """Build a market scene without decision-making."""
        created_at = datetime.now().astimezone().isoformat()
        return MarketScene(
            id=f"market_scene:{semantic_scene.frame_sha256}",
            source_visual_scene_id=visual_scene.id,
            source_semantic_scene_id=semantic_scene.id,
            source_frame=semantic_scene.source_frame,
            frame_sha256=semantic_scene.frame_sha256,
            created_at=created_at,
            visual_scene=visual_scene,
            semantic_scene=semantic_scene,
            market_elements=market_elements,
            price_regions=price_regions,
            time_regions=time_regions,
            metadata={
                "structural_only": True,
                "value_interpreted": False,
                "operation_interpreted": False,
                "ai": False,
                "llm": False,
                "strategy": False,
                "decision_making": False,
            },
        )
