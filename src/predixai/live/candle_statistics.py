"""Live candle statistics metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CandleStatistics:
    session_id: str
    timeframe: str
    average: float
    maximum: float
    minimum: float
    amplitude: float
    volatility: float
    sample_count: int
    price_points: tuple[float, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "average": self.average,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "amplitude": self.amplitude,
            "volatility": self.volatility,
            "sample_count": self.sample_count,
            "price_points": list(self.price_points),
            "metadata": dict(self.metadata),
        }
