"""Unified market structure metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_entity import MarketEntities
from predixai.vision.visual.market_entity_registry import MarketEntityRegistry
from predixai.vision.visual.market_scene import MarketScene
from predixai.vision.visual.visual_snapshot import VisualSnapshot


@dataclass(frozen=True)
class MarketStructure:
    """Structural market representation without interpretation or decisions."""

    id: str
    source_visual_snapshot_id: str
    source_market_scene_id: str
    source_frame: str
    frame_sha256: str
    created_at: str
    visual_snapshot: VisualSnapshot
    market_scene: MarketScene
    market_entities: MarketEntities
    entity_registry: MarketEntityRegistry
    ocr_result: object
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def entity_count(self) -> int:
        return self.market_entities.count

    @property
    def region_count(self) -> int:
        return self.market_entities.region_count

    @property
    def element_count(self) -> int:
        return self.market_scene.element_count

    @property
    def snapshot_region_count(self) -> int:
        return self.visual_snapshot.structured_ocr.total_regions

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_visual_snapshot_id": self.source_visual_snapshot_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_frame": self.source_frame,
            "frame_sha256": self.frame_sha256,
            "created_at": self.created_at,
            "visual_snapshot": self.visual_snapshot.to_dict(),
            "market_scene": self.market_scene.to_dict(),
            "market_entities": self.market_entities.to_dict(),
            "entity_registry": self.entity_registry.to_dict(),
            "ocr_result": self.ocr_result.to_dict() if hasattr(self.ocr_result, "to_dict") else self.ocr_result,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "element_count": self.element_count,
            "snapshot_region_count": self.snapshot_region_count,
            "metadata": dict(self.metadata),
        }
