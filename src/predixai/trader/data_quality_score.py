"""Data quality scoring for PredixAI Trader observer evidence.

V1 scope: determine whether observed market data is usable for memory.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataQualityScoreResult:
    score: float
    label: str
    usable_for_memory: bool
    factors: dict[str, float]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "label": self.label,
            "usable_for_memory": self.usable_for_memory,
            "factors": dict(self.factors),
            "warnings": list(self.warnings),
        }


class DataQualityScorer:
    """Score live evidence quality before it becomes market memory."""

    def score_evidence(self, payload: dict[str, Any]) -> DataQualityScoreResult:
        factors: dict[str, float] = {}
        warnings: list[str] = []

        price = self.extract_price(payload)
        if price is not None:
            factors["price_detected"] = 30.0
        else:
            factors["price_missing"] = -25.0
            warnings.append("price_missing")

        candle_snapshot = payload.get("candle_snapshot")
        if isinstance(candle_snapshot, dict) and candle_snapshot:
            factors["candle_snapshot_present"] = 15.0
        else:
            factors["candle_snapshot_missing"] = -15.0
            warnings.append("candle_snapshot_missing")

        candle_statistics = payload.get("candle_statistics")
        if isinstance(candle_statistics, dict) and candle_statistics:
            factors["candle_statistics_present"] = 15.0
        else:
            factors["candle_statistics_missing"] = -10.0
            warnings.append("candle_statistics_missing")

        field_values = _nested_get(payload, ("candle_snapshot", "field_values"))
        if isinstance(field_values, list) and field_values:
            factors["field_values_present"] = 15.0
        else:
            factors["field_values_missing"] = -10.0
            warnings.append("field_values_missing")

        unknown_fields = _nested_get(payload, ("candle_snapshot", "unknown_fields"))
        if isinstance(unknown_fields, list):
            if len(unknown_fields) == 0:
                factors["unknown_fields_clean"] = 10.0
            else:
                penalty = min(20.0, float(len(unknown_fields)) * 5.0)
                factors["unknown_fields_penalty"] = -penalty
                warnings.append(f"unknown_fields:{len(unknown_fields)}")
        else:
            factors["unknown_fields_absent"] = 0.0

        if payload.get("live_candle_benchmark") or payload.get("live_validation_benchmark"):
            factors["benchmark_present"] = 10.0
        else:
            factors["benchmark_missing"] = -5.0
            warnings.append("benchmark_missing")

        if _has_timestamp(payload):
            factors["timestamp_present"] = 5.0
        else:
            factors["timestamp_missing"] = -5.0
            warnings.append("timestamp_missing")

        if _has_asset(payload):
            factors["asset_present"] = 5.0
        else:
            factors["asset_missing"] = -5.0
            warnings.append("asset_missing")

        if _has_timeframe(payload):
            factors["timeframe_present"] = 5.0
        else:
            factors["timeframe_missing"] = -5.0
            warnings.append("timeframe_missing")

        raw_score = 40.0 + sum(factors.values())
        final_score = max(0.0, min(100.0, round(raw_score, 2)))
        label = _label(final_score)
        usable = final_score >= 60.0 and price is not None

        return DataQualityScoreResult(
            score=final_score,
            label=label,
            usable_for_memory=usable,
            factors=factors,
            warnings=tuple(warnings),
        )

    def extract_price(self, payload: dict[str, Any]) -> float | None:
        direct_candidates = (
            payload.get("price"),
            _nested_get(payload, ("candle_statistics", "close")),
            _nested_get(payload, ("candle_statistics", "last")),
            _nested_get(payload, ("candle_statistics", "average")),
            _nested_get(payload, ("live_candle_benchmark", "average")),
        )
        for candidate in direct_candidates:
            parsed = _parse_number(candidate)
            if parsed is not None:
                return parsed

        field_values = _nested_get(payload, ("candle_snapshot", "field_values"))
        if isinstance(field_values, list):
            for item in field_values:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("field_name") or item.get("name") or "").lower()
                if "price" not in name and "preco" not in name and "cotacao" not in name:
                    continue
                for key in ("value", "raw_value", "text", "normalized_value"):
                    parsed = _parse_number(item.get(key))
                    if parsed is not None:
                        return parsed

        return None


def _label(score: float) -> str:
    if score >= 90.0:
        return "EXCELLENT"
    if score >= 75.0:
        return "GOOD"
    if score >= 60.0:
        return "FAIR"
    return "POOR"


def _has_timestamp(payload: dict[str, Any]) -> bool:
    candidates = (
        payload.get("captured_at"),
        payload.get("created_at"),
        payload.get("generated_at"),
        _nested_get(payload, ("candle_snapshot", "captured_at")),
        _nested_get(payload, ("candle_snapshot", "created_at")),
    )
    return any(candidate is not None and str(candidate).strip() for candidate in candidates)


def _has_asset(payload: dict[str, Any]) -> bool:
    candidates = (
        payload.get("asset"),
        _nested_get(payload, ("session", "asset")),
        _nested_get(payload, ("metadata", "asset")),
    )
    return any(candidate is not None and str(candidate).strip() for candidate in candidates)


def _has_timeframe(payload: dict[str, Any]) -> bool:
    candidates = (
        payload.get("timeframe"),
        _nested_get(payload, ("candle_snapshot", "timeframe")),
        _nested_get(payload, ("session", "timeframe")),
        _nested_get(payload, ("metadata", "timeframe")),
    )
    return any(candidate is not None and str(candidate).strip() for candidate in candidates)


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    if not match:
        return None

    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None
