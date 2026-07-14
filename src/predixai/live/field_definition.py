"""Live candle field definition metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VISUAL_REGION_CLASSIFICATIONS = frozenset(
    {
        "STATIC_POSITION",
        "DYNAMIC_CONTENT",
        "CONDITIONAL_VISIBILITY",
        "ASSET_DEPENDENT",
        "ORDER_MODE_DEPENDENT",
    }
)


@dataclass(frozen=True)
class VisualRegionSpecification:
    """Immutable semantic contract for one authorized broker-client region."""

    region_id: str
    purpose: str
    classifications: tuple[str, ...]
    source: str
    reading_mode: str
    expected_data_type: str
    normalization_rule: str
    visibility_state: str = "ALWAYS"
    parent_region_id: str | None = None
    privacy_sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.region_id.strip() or self.region_id != self.region_id.upper():
            raise ValueError("visual region id must be non-empty uppercase text")
        if not self.classifications:
            raise ValueError("visual region classifications are required")
        unknown = set(self.classifications) - VISUAL_REGION_CLASSIFICATIONS
        if unknown:
            raise ValueError(f"unknown visual region classifications: {sorted(unknown)}")
        if self.reading_mode not in {"OCR", "VISUAL_STATE"}:
            raise ValueError("visual region reading mode must be OCR or VISUAL_STATE")
        if self.visibility_state not in {"ALWAYS", "POPUP_OPEN"}:
            raise ValueError("unsupported visual region visibility state")

    @property
    def requires_ocr(self) -> bool:
        return self.reading_mode == "OCR"


@dataclass(frozen=True)
class FieldDefinition:
    field_name: str
    region_id: str
    region_name: str
    purpose: str
    patterns: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    relative_geometry: tuple[float, float, float, float] | None = None
    expected_data_type: str = "TEXT"
    normalization_rule: str = "PRESERVE"
    min_confidence: float = 0.0
    required: bool = False
    failure_behavior: str = "UNKNOWN"

    @property
    def field_id(self) -> str:
        return self.field_name.strip().upper()

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "purpose": self.purpose,
            "patterns": list(self.patterns),
            "metadata": dict(self.metadata),
            "field_id": self.field_id,
            "relative_geometry": (
                {
                    "x_ratio": self.relative_geometry[0],
                    "y_ratio": self.relative_geometry[1],
                    "width_ratio": self.relative_geometry[2],
                    "height_ratio": self.relative_geometry[3],
                }
                if self.relative_geometry is not None
                else None
            ),
            "expected_data_type": self.expected_data_type,
            "normalization_rule": self.normalization_rule,
            "min_confidence": self.min_confidence,
            "required_or_optional": "REQUIRED" if self.required else "OPTIONAL",
            "failure_behavior": self.failure_behavior,
        }
