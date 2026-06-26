"""Live validation report metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.live_market_reading import LiveMarketReading


@dataclass(frozen=True)
class LiveValidationReport:
    session_id: str
    total_captures: int
    fields_detected: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    ocr_confidence: float
    total_time_ms: float
    status: str
    readings: tuple[LiveMarketReading, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "total_captures": self.total_captures,
            "fields_detected": list(self.fields_detected),
            "unknown_fields": list(self.unknown_fields),
            "ocr_confidence": self.ocr_confidence,
            "total_time_ms": self.total_time_ms,
            "status": self.status,
            "readings": [reading.to_dict() for reading in self.readings],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LiveValidationSummary:
    total_captures: int
    detected_fields: int
    unknown_fields: int
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "total_captures": self.total_captures,
            "detected_fields": self.detected_fields,
            "unknown_fields": self.unknown_fields,
            "status": self.status,
        }
