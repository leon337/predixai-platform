"""Locate live candle fields in the observed interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.field_definition import FieldDefinition


@dataclass(frozen=True)
class FieldLocationMap:
    definitions: tuple[FieldDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "definitions": [definition.to_dict() for definition in self.definitions],
            "metadata": dict(self.metadata),
        }


class FieldLocator:
    """Deterministic field locator for M1 candle validation."""

    def locate(self, *, window_title: str, timeframe: str) -> FieldLocationMap:
        definitions = (
            FieldDefinition(
                field_name="asset",
                region_id="FULL_SCREEN",
                region_name="Full Screen",
                purpose="identified_asset",
                patterns=(r"\b[A-Z]{3,6}/[A-Z]{3,6}\b", r"\b[A-Z]{3,6}\b"),
            ),
            FieldDefinition(
                field_name="price",
                region_id="FULL_SCREEN",
                region_name="Full Screen",
                purpose="identified_price",
                patterns=(r"\b\d+[.,]\d+\b",),
            ),
            FieldDefinition(
                field_name="time",
                region_id="FULL_SCREEN",
                region_name="Full Screen",
                purpose="identified_time",
                patterns=(r"\b\d{2}:\d{2}(:\d{2})?\b",),
            ),
            FieldDefinition(
                field_name="payout",
                region_id="FULL_SCREEN",
                region_name="Full Screen",
                purpose="identified_payout",
                patterns=(r"payout[:\s]*\d+%?", r"\b\d+%\s*payout\b"),
            ),
            FieldDefinition(
                field_name="balance",
                region_id="FULL_SCREEN",
                region_name="Full Screen",
                purpose="identified_balance",
                patterns=(r"balance[:\s]*\$\s*\d+[.,]?\d*", r"\bsaldo\b"),
            ),
        )
        return FieldLocationMap(
            definitions=definitions,
            metadata={
                "window_title": window_title,
                "timeframe": timeframe,
                "region_count": len(definitions),
            },
        )
