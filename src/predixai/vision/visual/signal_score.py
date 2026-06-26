"""Structural signal score metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalScore:
    value: float
    rule: str
    confidence: float
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "rule": self.rule,
            "confidence": self.confidence,
            "status": self.status,
        }
