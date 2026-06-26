"""Live candle snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.field_value import FieldValue
from predixai.live.live_market_reading import LiveMarketReading


@dataclass(frozen=True)
class CandleSnapshot:
    session_id: str
    timeframe: str
    capture_count: int
    readings: tuple[LiveMarketReading, ...]
    field_values: tuple[FieldValue, ...]
    field_names: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "capture_count": self.capture_count,
            "readings": [reading.to_dict() for reading in self.readings],
            "field_values": [field_value.to_dict() for field_value in self.field_values],
            "field_names": list(self.field_names),
            "unknown_fields": list(self.unknown_fields),
            "metadata": dict(self.metadata),
        }
