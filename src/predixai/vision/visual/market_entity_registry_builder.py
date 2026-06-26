"""Build market entity registries."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_entity import MarketEntities
from predixai.vision.visual.market_entity_registry import MarketEntityRegistry


class MarketEntityRegistryBuilder:
    """Create a registry from market entities."""

    def build(self, market_entities: MarketEntities) -> MarketEntityRegistry:
        """Build a registry for market entities."""
        created_at = datetime.now().astimezone().isoformat()
        return MarketEntityRegistry(
            id=f"market_entity_registry:{market_entities.source_market_scene_id}",
            source_market_scene_id=market_entities.source_market_scene_id,
            source_visual_scene_id=market_entities.source_visual_scene_id,
            source_frame=market_entities.source_frame,
            created_at=created_at,
            entities=market_entities.entities,
            metadata={
                "entity_count": market_entities.count,
                "region_count": market_entities.region_count,
                "structural_only": True,
                "ai": False,
                "llm": False,
            },
        )
