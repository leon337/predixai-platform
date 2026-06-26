"""Extract live candle fields from OCR readings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.field_definition import FieldDefinition
from predixai.live.field_locator import FieldLocationMap
from predixai.live.field_value import FieldValue
from predixai.live.live_market_reading import LiveMarketReading


@dataclass(frozen=True)
class FieldExtractionResult:
    fields: tuple[FieldValue, ...]
    unknown_fields: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "fields": [field_value.to_dict() for field_value in self.fields],
            "unknown_fields": list(self.unknown_fields),
            "metadata": dict(self.metadata),
        }


class FieldExtractor:
    """Extracts deterministic live candle fields from reading metadata."""

    def extract(
        self,
        reading: LiveMarketReading,
        locator: FieldLocationMap,
    ) -> FieldExtractionResult:
        values = []
        unknown_fields = []
        source_map = {
            "asset": reading.asset,
            "price": reading.price,
            "time": reading.time,
            "payout": reading.payout,
            "balance": reading.balance,
        }
        for definition in locator.definitions:
            raw_value = str(source_map.get(definition.field_name, "UNKNOWN") or "UNKNOWN")
            normalized_value = raw_value if raw_value != "UNKNOWN" else "UNKNOWN"
            status = "FOUND" if normalized_value != "UNKNOWN" else "UNKNOWN"
            if status == "UNKNOWN":
                unknown_fields.append(definition.field_name)
            values.append(
                FieldValue(
                    field_name=definition.field_name,
                    raw_value=raw_value,
                    normalized_value=normalized_value,
                    region_id=definition.region_id,
                    confidence=float(reading.confidence),
                    status=status,
                    metadata={
                        "region_name": definition.region_name,
                        "purpose": definition.purpose,
                        "patterns": list(definition.patterns),
                    },
                )
            )
        return FieldExtractionResult(
            fields=tuple(values),
            unknown_fields=tuple(unknown_fields),
            metadata={
                "timeframe": reading.timeframe,
                "source_confidence": float(reading.confidence),
                "field_count": len(values),
            },
        )
