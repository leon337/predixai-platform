"""Locate live candle fields in the observed interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.field_definition import FieldDefinition, VisualRegionSpecification


AUTHORIZED_VISUAL_REGION_SPECS = (
    VisualRegionSpecification("ASSET", "Selected asset card", ("STATIC_POSITION", "DYNAMIC_CONTENT", "ASSET_DEPENDENT"), "BROKER_ASSET_CARD", "OCR", "ASSET_TEXT", "NORMALIZE_SPACES_PRESERVE_OTC_REJECT_MULTIPLE"),
    VisualRegionSpecification("PAYOUT", "Asset payout percentage", ("STATIC_POSITION", "DYNAMIC_CONTENT", "ASSET_DEPENDENT"), "BROKER_ASSET_CARD_PAYOUT", "OCR", "PERCENTAGE", "EXACTLY_ONE_PERCENTAGE_RANGE_0_100", "ALWAYS", "ASSET"),
    VisualRegionSpecification("PRICE_SOURCE_BROWSER_TAB", "Price and asset in the active browser tab", ("DYNAMIC_CONTENT", "ASSET_DEPENDENT"), "ACTIVE_BROWSER_TAB_VISUAL_TITLE", "OCR", "PRICE_AND_ASSET", "ACTIVE_TAB_EXACT_PRICE_ASSET_CROSS_CHECK"),
    VisualRegionSpecification("TIMEFRAME", "Selected chart timeframe", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "CHART_TIMEFRAME_CONTROL", "OCR", "TIMEFRAME_TOKEN", "EXACTLY_ONE_ALLOWED_TIMEFRAME"),
    VisualRegionSpecification("ENTRY_VALUE", "Configured simulated entry value", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "ORDER_ENTRY_VALUE", "OCR", "DECIMAL_TEXT", "EXACTLY_ONE_NUMERIC_VALUE"),
    VisualRegionSpecification("ENTRY_VALUE_MINUS", "Decrease entry value control", ("STATIC_POSITION",), "ORDER_ENTRY_MINUS_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("ENTRY_VALUE_PLUS", "Increase entry value control", ("STATIC_POSITION",), "ORDER_ENTRY_PLUS_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("DURATION", "Configured simulated order duration", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "ORDER_DURATION_VALUE", "OCR", "DURATION_TEXT", "EXACTLY_ONE_DURATION"),
    VisualRegionSpecification("DURATION_MINUS", "Decrease duration control", ("STATIC_POSITION",), "ORDER_DURATION_MINUS_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("DURATION_PLUS", "Increase duration control", ("STATIC_POSITION",), "ORDER_DURATION_PLUS_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("ENABLE_ORDERS", "Pending-order enablement control", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "ENABLE_ORDERS_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("UP_BUTTON", "Up-direction action control", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "UP_DIRECTION_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("DOWN_BUTTON", "Down-direction action control", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "DOWN_DIRECTION_CONTROL", "VISUAL_STATE", "CONTROL_STATE", "PRESENCE_AND_ENABLED_STATE"),
    VisualRegionSpecification("PROFIT_DISPLAY", "Displayed potential profit", ("STATIC_POSITION", "DYNAMIC_CONTENT", "ASSET_DEPENDENT"), "ORDER_PROFIT_DISPLAY", "OCR", "DECIMAL_TEXT", "EXACTLY_ONE_NUMERIC_VALUE"),
    VisualRegionSpecification("ACCOUNT_BALANCE", "Displayed account balance", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "ACCOUNT_BALANCE_DISPLAY", "OCR", "DECIMAL_TEXT", "LOCAL_ONLY_REDACT_REPORT", privacy_sensitive=True),
    VisualRegionSpecification("ACCOUNT_TYPE", "Displayed account type", ("STATIC_POSITION", "DYNAMIC_CONTENT"), "ACCOUNT_TYPE_DISPLAY", "OCR", "ACCOUNT_TYPE_TEXT", "LOCAL_ONLY_REDACT_REPORT", privacy_sensitive=True),
)

AUTHORIZED_VISUAL_REGION_BY_ID = {
    specification.region_id: specification
    for specification in AUTHORIZED_VISUAL_REGION_SPECS
}


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

    def build_authorized_region_contracts(
        self,
        geometries: dict[str, tuple[float, float, float, float]],
        *,
        min_confidence: float = 80.0,
    ) -> FieldLocationMap:
        """Build the complete C.1A visual map after manual client calibration."""
        expected_ids = set(AUTHORIZED_VISUAL_REGION_BY_ID)
        if set(geometries) != expected_ids:
            raise ValueError(f"exactly {len(expected_ids)} authorized visual region geometries are required")
        definitions = tuple(
            FieldDefinition(
                field_name=specification.region_id.lower(),
                region_id=specification.region_id,
                region_name=specification.region_id.replace("_", " ").title(),
                purpose=specification.purpose,
                relative_geometry=geometries[specification.region_id],
                expected_data_type=specification.expected_data_type,
                normalization_rule=specification.normalization_rule,
                min_confidence=float(min_confidence),
                required=True,
                failure_behavior="FAIL_CLOSED_PRESERVE_LAST_VALID_READING",
                metadata={
                    "calibration_stage": "PTP-GOV.4.6C.1A",
                    "classifications": specification.classifications,
                    "source": specification.source,
                    "reading_mode": specification.reading_mode,
                    "visibility_state": specification.visibility_state,
                    "parent_region_id": specification.parent_region_id,
                    "privacy_sensitive": specification.privacy_sensitive,
                    "prohibited_area": False,
                },
            )
            for specification in AUTHORIZED_VISUAL_REGION_SPECS
        )
        return FieldLocationMap(
            definitions=definitions,
            metadata={
                "region_count": len(AUTHORIZED_VISUAL_REGION_SPECS),
                "independent_regions": False,
                "hierarchical_regions": True,
                "full_screen_fallback": "PROHIBITED",
                "broker_time_region_required": False,
                "time_source": "SYSTEM_CLOCK",
                "popup_calibration": "EXCLUDED_FROM_FIXED_MAP",
            },
        )
