"""Read basic live market fields from OCR text."""

from __future__ import annotations

import re

from predixai.live.live_market_reading import LiveMarketReading


class LiveMarketReader:
    def read(self, ocr_text: str, ocr_confidence: float, timeframe: str) -> LiveMarketReading:
        text = ocr_text or ""
        asset = self._match(text, [r"\b[A-Z]{3,6}/[A-Z]{3,6}\b", r"\b[A-Z]{3,6}\b"])
        price = self._match(text, [r"\b\d+[.,]\d+\b"])
        time_value = self._match(text, [r"\b\d{2}:\d{2}(:\d{2})?\b"])
        balance = self._match(text, [r"balance[:\s]*\$\s*\d+[.,]?\d*", r"\bsaldo\b"])
        payout = self._match(text, [r"payout[:\s]*\d+%?", r"\b\d+% payout\b"])
        return LiveMarketReading(
            asset=asset,
            price=price,
            time=time_value,
            balance=balance,
            payout=payout,
            timeframe=timeframe if timeframe else "UNKNOWN",
            confidence=ocr_confidence,
            source_ocr_text=text,
            metadata={
                "unknown_fields": [
                    key
                    for key, value in {
                        "asset": asset,
                        "price": price,
                        "time": time_value,
                        "balance": balance,
                        "payout": payout,
                        "timeframe": timeframe,
                    }.items()
                    if value == "UNKNOWN"
                ]
            },
        )

    def _match(self, text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return "UNKNOWN"
