"""Schedule live validation captures."""

from __future__ import annotations

from datetime import datetime
from predixai.live.live_capture_tick import LiveCaptureTick


class LiveCaptureScheduler:
    def schedule(self, total_ticks: int, interval_seconds: int) -> tuple[LiveCaptureTick, ...]:
        ticks: list[LiveCaptureTick] = []
        for index in range(total_ticks):
            ticks.append(
                LiveCaptureTick(
                    tick_index=index + 1,
                    captured_at=datetime.now().astimezone().isoformat(),
                    capture_path="",
                    window_title="",
                    metadata={"interval_seconds": interval_seconds},
                )
            )
        return tuple(ticks)
