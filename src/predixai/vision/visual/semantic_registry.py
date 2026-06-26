"""Registry of deterministic semantic entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticEntity:
    """Registered semantic entity for future reuse."""

    id: str
    stable_key: str
    semantic_element_id: str
    source_object_id: str
    region_id: str
    semantic_type: str
    labels: tuple[str, ...]
    first_seen_scene_id: str
    last_seen_scene_id: str
    observation_count: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "stable_key": self.stable_key,
            "semantic_element_id": self.semantic_element_id,
            "source_object_id": self.source_object_id,
            "region_id": self.region_id,
            "semantic_type": self.semantic_type,
            "labels": list(self.labels),
            "first_seen_scene_id": self.first_seen_scene_id,
            "last_seen_scene_id": self.last_seen_scene_id,
            "observation_count": self.observation_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticRegistry:
    """Registry of semantic entities for one semantic scene."""

    id: str
    source_scene_id: str
    source_frame: str
    created_at: str
    entities: tuple[SemanticEntity, ...]

    @property
    def count(self) -> int:
        """Return the number of registered semantic entities."""
        return len(self.entities)

    @property
    def label_count(self) -> int:
        """Return the total labels attached to registered entities."""
        return sum(len(entity.labels) for entity in self.entities)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_scene_id": self.source_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "label_count": self.label_count,
            "entities": [entity.to_dict() for entity in self.entities],
        }
