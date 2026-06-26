"""Registry and serialization for structural market entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_entity import MarketEntities, MarketEntity
from predixai.vision.visual.market_entity_storage import EntityStorage


@dataclass(frozen=True)
class MarketEntityRegistry:
    """Registry of market entities for one market scene."""

    id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    entities: tuple[MarketEntity, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.entities)

    @property
    def region_count(self) -> int:
        return len({entity.region_id for entity in self.entities})

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "region_count": self.region_count,
            "entities": [entity.to_dict() for entity in self.entities],
            "metadata": dict(self.metadata),
        }


EntityRegistry = MarketEntityRegistry


class EntitySerializer:
    """Serialize market entities to dictionaries."""

    def serialize(self, registry: MarketEntityRegistry) -> dict[str, object]:
        return registry.to_dict()
