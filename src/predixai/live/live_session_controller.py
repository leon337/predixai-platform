"""Control live validation sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from predixai.live.live_session import LiveSession
from predixai.live.live_session_state import LiveSessionState


class LiveSessionController:
    def start(
        self,
        timeframe: str,
        capture_interval_seconds: int,
        captures_per_candle: int,
        validation_candles: int = 1,
    ) -> LiveSession:
        started_at = datetime.now().astimezone().isoformat()
        state = LiveSessionState(
            state="RUNNING",
            started_at=started_at,
            updated_at=started_at,
            metadata={"transition": "STARTED"},
        )
        return LiveSession(
            session_id=str(uuid4()),
            timeframe=timeframe,
            capture_interval_seconds=capture_interval_seconds,
            captures_per_candle=captures_per_candle,
            validation_candles=validation_candles,
            started_at=started_at,
            state=state,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
