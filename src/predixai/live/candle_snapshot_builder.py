"""Build live candle snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.candle_snapshot import CandleSnapshot
from predixai.live.field_extractor import FieldExtractionResult
from predixai.live.field_locator import FieldLocationMap
from predixai.live.live_market_reading import LiveMarketReading


@dataclass(frozen=True)
class CandleSnapshotBuildResult:
    snapshot: CandleSnapshot
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "metadata": dict(self.metadata),
        }


class CandleSnapshotBuilder:
    """Build a candle snapshot from live readings."""

    def build(
        self,
        *,
        session_id: str,
        timeframe: str,
        readings: tuple[LiveMarketReading, ...],
        extraction_results: tuple[FieldExtractionResult, ...],
        locator: FieldLocationMap,
    ) -> CandleSnapshotBuildResult:
        field_values = tuple(
            field_value
            for extraction in extraction_results
            for field_value in extraction.fields
        )
        field_names = tuple(dict.fromkeys(field_value.field_name for field_value in field_values))
        unknown_fields = tuple(
            dict.fromkeys(
                field_name
                for extraction in extraction_results
                for field_name in extraction.unknown_fields
            )
        )
        snapshot = CandleSnapshot(
            session_id=session_id,
            timeframe=timeframe,
            capture_count=len(readings),
            readings=readings,
            field_values=field_values,
            field_names=field_names,
            unknown_fields=unknown_fields,
            metadata={
                "region_count": len(locator.definitions),
                "field_extractions": len(extraction_results),
            },
        )
        return CandleSnapshotBuildResult(
            snapshot=snapshot,
            metadata={
                "session_id": session_id,
                "timeframe": timeframe,
                "capture_count": len(readings),
                "field_count": len(field_names),
                "unknown_field_count": len(unknown_fields),
            },
        )
