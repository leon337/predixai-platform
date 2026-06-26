"""Live market reading metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveMarketReading:
    asset: str
    price: str
    time: str
    balance: str
    payout: str
    timeframe: str
    confidence: float
    source_ocr_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "asset": self.asset,
            "price": self.price,
            "time": self.time,
            "balance": self.balance,
            "payout": self.payout,
            "timeframe": self.timeframe,
            "confidence": self.confidence,
            "source_ocr_text": self.source_ocr_text,
            "metadata": dict(self.metadata),
        }
