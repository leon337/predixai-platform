"""Build live candle statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any

from predixai.live.candle_snapshot import CandleSnapshot
from predixai.live.candle_statistics import CandleStatistics
from predixai.live.field_value import FieldValue


@dataclass(frozen=True)
class CandleStatisticsBuildResult:
    statistics: CandleStatistics
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "statistics": self.statistics.to_dict(),
            "metadata": dict(self.metadata),
        }


class CandleStatisticsBuilder:
    """Build descriptive statistics for a live candle."""

    def build(self, snapshot: CandleSnapshot) -> CandleStatisticsBuildResult:
        price_points = tuple(self._parse_price(field_value) for field_value in snapshot.field_values if field_value.field_name == "price" and self._parse_price(field_value) is not None)
        parsed_prices = tuple(value for value in price_points if value is not None)
        numeric_prices = tuple(float(value) for value in parsed_prices)
        if numeric_prices:
            average = round(mean(numeric_prices), 6)
            maximum = round(max(numeric_prices), 6)
            minimum = round(min(numeric_prices), 6)
            amplitude = round(maximum - minimum, 6)
            volatility = round(pstdev(numeric_prices) if len(numeric_prices) > 1 else 0.0, 6)
        else:
            average = maximum = minimum = amplitude = volatility = 0.0
        statistics = CandleStatistics(
            session_id=snapshot.session_id,
            timeframe=snapshot.timeframe,
            average=average,
            maximum=maximum,
            minimum=minimum,
            amplitude=amplitude,
            volatility=volatility,
            sample_count=snapshot.capture_count,
            price_points=numeric_prices,
            metadata={
                "field_count": len(snapshot.field_names),
                "unknown_field_count": len(snapshot.unknown_fields),
            },
        )
        return CandleStatisticsBuildResult(
            statistics=statistics,
            metadata={
                "session_id": snapshot.session_id,
                "timeframe": snapshot.timeframe,
                "sample_count": snapshot.capture_count,
                "average": average,
                "maximum": maximum,
                "minimum": minimum,
                "volatility": volatility,
            },
        )

    def _parse_price(self, field_value: FieldValue) -> float | None:
        if field_value.normalized_value == "UNKNOWN":
            return None
        normalized = field_value.normalized_value.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None
