"""Live session metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.live.live_session_state import LiveSessionState


@dataclass(frozen=True)
class LiveSession:
    session_id: str
    timeframe: str
    capture_interval_seconds: int
    captures_per_candle: int
    validation_candles: int
    started_at: str
    state: LiveSessionState
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "capture_interval_seconds": self.capture_interval_seconds,
            "captures_per_candle": self.captures_per_candle,
            "validation_candles": self.validation_candles,
            "started_at": self.started_at,
            "state": self.state.to_dict(),
            "metadata": dict(self.metadata),
        }
