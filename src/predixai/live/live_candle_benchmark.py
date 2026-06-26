"""Benchmark for the live candle analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from predixai.live.candle_snapshot import CandleSnapshot
from predixai.live.candle_statistics import CandleStatistics


@dataclass(frozen=True)
class LiveCandleBenchmark:
    enabled: bool
    started_at: str
    finished_at: str
    processing_time_ms: float
    capture_count: int
    field_count: int
    average: float
    maximum: float
    minimum: float
    volatility: float
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "processing_time_ms": self.processing_time_ms,
            "capture_count": self.capture_count,
            "field_count": self.field_count,
            "average": self.average,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "volatility": self.volatility,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LiveCandleBenchmarkRun:
    started_at: str
    started_at_perf: float
    enabled: bool = True


@dataclass(frozen=True)
class LiveCandleBenchmarkResult:
    benchmark: LiveCandleBenchmark
    metadata: dict[str, Any] = field(default_factory=dict)


class LiveCandleBenchmarkBuilder:
    """Build live candle benchmark data."""

    def start(self, enabled: bool = True) -> LiveCandleBenchmarkRun:
        from datetime import datetime

        return LiveCandleBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            started_at_perf=perf_counter(),
            enabled=enabled,
        )

    def finish(
        self,
        run: LiveCandleBenchmarkRun,
        snapshot: CandleSnapshot,
        statistics: CandleStatistics,
    ) -> LiveCandleBenchmarkResult:
        from datetime import datetime

        finished_at_perf = perf_counter()
        benchmark = LiveCandleBenchmark(
            enabled=run.enabled,
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            processing_time_ms=round((finished_at_perf - run.started_at_perf) * 1000, 3),
            capture_count=snapshot.capture_count,
            field_count=len(snapshot.field_names),
            average=statistics.average,
            maximum=statistics.maximum,
            minimum=statistics.minimum,
            volatility=statistics.volatility,
            status="LIVE_CANDLE_COMPLETED",
            metadata={
                "session_id": snapshot.session_id,
                "timeframe": snapshot.timeframe,
                "unknown_fields": list(snapshot.unknown_fields),
                "sample_count": statistics.sample_count,
            },
        )
        return LiveCandleBenchmarkResult(
            benchmark=benchmark,
            metadata={
                "session_id": snapshot.session_id,
                "status": benchmark.status,
            },
        )
