"""Validate the market structure layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.market_structure import MarketStructure


@dataclass(frozen=True)
class MarketStructureValidation:
    """Validation result for the market structure."""

    valid: bool
    issues: tuple[str, ...]
    entity_count: int
    region_count: int
    element_count: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "element_count": self.element_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class MarketStructureValidator:
    """Validate structural consistency across the market structure."""

    def validate(self, market_structure: MarketStructure) -> MarketStructureValidation:
        issues: list[str] = []
        self._validate_snapshot(market_structure, issues)
        self._validate_entities(market_structure, issues)
        self._validate_regions(market_structure, issues)
        self._validate_ocr(market_structure, issues)
        return MarketStructureValidation(
            valid=not issues,
            issues=tuple(issues),
            entity_count=market_structure.entity_count,
            region_count=market_structure.region_count,
            element_count=market_structure.element_count,
            created_at=market_structure.created_at,
            metadata={
                "source_market_scene_id": market_structure.source_market_scene_id,
                "structural_only": True,
                "ai": False,
                "llm": False,
            },
        )

    def _validate_snapshot(self, market_structure: MarketStructure, issues: list[str]) -> None:
        if not market_structure.source_visual_snapshot_id:
            issues.append("snapshot_id_missing")
        if market_structure.visual_snapshot.structured_ocr.total_regions <= 0:
            issues.append("snapshot_regions_missing")

    def _validate_entities(self, market_structure: MarketStructure, issues: list[str]) -> None:
        if market_structure.entity_count <= 0:
            issues.append("entity_count_invalid")

    def _validate_regions(self, market_structure: MarketStructure, issues: list[str]) -> None:
        if market_structure.region_count <= 0:
            issues.append("region_count_invalid")

    def _validate_ocr(self, market_structure: MarketStructure, issues: list[str]) -> None:
        ocr_result = market_structure.ocr_result
        if ocr_result is None:
            issues.append("ocr_missing")
            return
        if not getattr(ocr_result, "image_sha256", ""):
            issues.append("ocr_sha256_missing")
