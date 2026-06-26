"""Live candle field value metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldValue:
    field_name: str
    raw_value: str
    normalized_value: str
    region_id: str
    confidence: float
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "region_id": self.region_id,
            "confidence": self.confidence,
            "status": self.status,
            "metadata": dict(self.metadata),
        }
