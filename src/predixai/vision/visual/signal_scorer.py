"""Score structural signals."""

from __future__ import annotations

from predixai.vision.visual.signal import Signals
from predixai.vision.visual.signal_score import SignalScore


class SignalScorer:
    def score(self, signals: Signals) -> tuple[SignalScore, ...]:
        return tuple(
            SignalScore(
                value=1.0,
                rule="structural_signal_rule",
                confidence=1.0,
                status="STRUCTURAL_READY",
            )
            for _ in signals.signals
        )
