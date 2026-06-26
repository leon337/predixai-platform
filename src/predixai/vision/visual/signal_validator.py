"""Validate structural signals."""

from __future__ import annotations

from dataclasses import dataclass, field

from predixai.vision.visual.signal import Signals


@dataclass(frozen=True)
class SignalValidation:
    valid: bool
    issues: tuple[str, ...]
    signal_count: int
    created_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "signal_count": self.signal_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class SignalValidator:
    def validate(self, signals: Signals) -> SignalValidation:
        issues: list[str] = []
        if signals.count == 0:
            issues.append("No signals available.")
        return SignalValidation(
            valid=not issues,
            issues=tuple(issues),
            signal_count=signals.count,
            created_at=signals.created_at,
            metadata={
                "source_intelligence_snapshot_id": signals.source_intelligence_snapshot_id,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
