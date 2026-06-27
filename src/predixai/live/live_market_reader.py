"""Read basic live market fields from OCR text."""

from __future__ import annotations

import re

from predixai.live.live_market_reading import LiveMarketReading


class LiveMarketReader:
    def read(self, ocr_text: str, ocr_confidence: float, timeframe: str) -> LiveMarketReading:
        text = ocr_text or ""

        asset = self._match(
            text,
            [
                r"\bLATAM Index\b",
                r"\b[A-Z]{3,6}/[A-Z]{3,6}(?:\s+OTC)?\b",
                r"\b[A-Z]{3,6}\b",
            ],
        )
        price = self._match(
            text,
            [
                r"Price[:\s]*(\d+[.,]\d+)",
                r"Window_Title:.*?\b(\d+[.,]\d+)\b",
                r"\b\d+[.,]\d+\b",
            ],
        )
        time_value = self._match(text, [r"\b\d{2}:\d{2}(?::\d{2})?\b"])
        balance = self._match(
            text,
            [
                r"Balance[:\s]*((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)",
                r"\b((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)\b",
                r"\bsaldo\b",
            ],
        )
        payout = self._match(
            text,
            [
                r"Payout[:\s]*(\d+%)",
                r"\b(\d+%)\b",
            ],
        )
        trade_value = self._match(
            text,
            [
                r"Trade[_\s-]*Value[:\s]*((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)",
                r"\b((?:R\$|RS|D)\s*\d+(?:[.,]\d+)*)\b",
            ],
        )
        duration = self._match(
            text,
            [
                r"Duration[:\s]*(\d+\s*min\.?)",
                r"\b(\d+\s*min\.?)\b",
            ],
        )

        return LiveMarketReading(
            asset=asset,
            price=price,
            time=time_value,
            balance=balance,
            payout=payout,
            timeframe=timeframe if timeframe else "UNKNOWN",
            confidence=ocr_confidence,
            source_ocr_text=text,
            trade_value=trade_value,
            duration=duration,
            metadata={
                "unknown_fields": [
                    key
                    for key, value in {
                        "asset": asset,
                        "price": price,
                        "balance": balance,
                        "payout": payout,
                        "trade_value": trade_value,
                        "duration": duration,
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
                groups = [value for value in match.groups() if value]
                value = groups[0] if groups else match.group(0)
                return value.strip().replace("RS", "R$")
        return "UNKNOWN"