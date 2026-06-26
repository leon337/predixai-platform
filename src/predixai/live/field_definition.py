"""Live candle field definition metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldDefinition:
    field_name: str
    region_id: str
    region_name: str
    purpose: str
    patterns: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "purpose": self.purpose,
            "patterns": list(self.patterns),
            "metadata": dict(self.metadata),
        }
