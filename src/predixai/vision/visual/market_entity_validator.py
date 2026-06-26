"""Validate structural market entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_entity import MarketEntity, MarketEntities


@dataclass(frozen=True)
class MarketEntityValidation:
    """Validation result for market entities."""

    valid: bool
    issues: tuple[str, ...]
    entity_count: int
    region_count: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class MarketEntityValidator:
    """Validate market entities structurally only."""

    def validate(self, market_entities: MarketEntities) -> MarketEntityValidation:
        """Validate entity structure without decision-making."""
        issues: list[str] = []
        seen_ids: set[str] = set()
        seen_keys: set[str] = set()
        for entity in market_entities.entities:
            self._validate_entity(entity, issues, seen_ids, seen_keys)

        return MarketEntityValidation(
            valid=not issues,
            issues=tuple(issues),
            entity_count=market_entities.count,
            region_count=market_entities.region_count,
            created_at=market_entities.created_at,
            metadata={
                "source_market_scene_id": market_entities.source_market_scene_id,
                "structural_only": True,
                "ai": False,
                "llm": False,
            },
        )

    def _validate_entity(
        self,
        entity: MarketEntity,
        issues: list[str],
        seen_ids: set[str],
        seen_keys: set[str],
    ) -> None:
        if not entity.id:
            issues.append("entity_id_missing")
        elif entity.id in seen_ids:
            issues.append(f"duplicate_entity_id:{entity.id}")
        else:
            seen_ids.add(entity.id)

        if not entity.stable_key:
            issues.append(f"stable_key_missing:{entity.id}")
        elif entity.stable_key in seen_keys:
            issues.append(f"duplicate_stable_key:{entity.stable_key}")
        else:
            seen_keys.add(entity.stable_key)

        if entity.width <= 0:
            issues.append(f"invalid_width:{entity.id}")
        if entity.height <= 0:
            issues.append(f"invalid_height:{entity.id}")
        if entity.x < 0 or entity.y < 0:
            issues.append(f"invalid_position:{entity.id}")
