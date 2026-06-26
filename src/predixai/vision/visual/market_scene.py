"""Unified market interface scene metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_element import MarketElements
from predixai.vision.visual.price_region_mapper import PriceRegionMapping
from predixai.vision.visual.semantic_scene import SemanticScene
from predixai.vision.visual.time_region_mapper import TimeRegionMapping
from predixai.vision.visual.visual_scene import VisualScene


@dataclass(frozen=True)
class MarketScene:
    """Structural market scene without operational interpretation."""

    id: str
    source_visual_scene_id: str
    source_semantic_scene_id: str
    source_frame: str
    frame_sha256: str
    created_at: str
    visual_scene: VisualScene
    semantic_scene: SemanticScene
    market_elements: MarketElements
    price_regions: PriceRegionMapping
    time_regions: TimeRegionMapping
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def element_count(self) -> int:
        """Return the number of market elements."""
        return self.market_elements.count

    @property
    def entity_count(self) -> int:
        """Return the number of market entities."""
        return self.market_elements.entity_count

    @property
    def price_region_count(self) -> int:
        """Return the number of mapped price regions."""
        return self.price_regions.count

    @property
    def time_region_count(self) -> int:
        """Return the number of mapped time regions."""
        return self.time_regions.count

    @property
    def region_count(self) -> int:
        """Return the number of unique regions represented by market metadata."""
        region_ids = {element.region_id for element in self.market_elements.elements}
        region_ids.update(region.region_id for region in self.price_regions.regions)
        region_ids.update(region.region_id for region in self.time_regions.regions)
        return len(region_ids)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_semantic_scene_id": self.source_semantic_scene_id,
            "source_frame": self.source_frame,
            "frame_sha256": self.frame_sha256,
            "created_at": self.created_at,
            "visual_scene": self.visual_scene.to_dict(),
            "semantic_scene": self.semantic_scene.to_dict(),
            "market_elements": self.market_elements.to_dict(),
            "price_regions": self.price_regions.to_dict(),
            "time_regions": self.time_regions.to_dict(),
            "element_count": self.element_count,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "price_region_count": self.price_region_count,
            "time_region_count": self.time_region_count,
            "metadata": dict(self.metadata),
        }
