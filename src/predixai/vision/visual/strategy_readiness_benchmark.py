"""Strategy readiness benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.strategy_readiness_snapshot import StrategyReadinessSnapshot


@dataclass(frozen=True)
class StrategyReadinessBenchmarkRun:
    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class StrategyReadinessBenchmarkResult:
    enabled: bool
    status: str
    started_at: str
    finished_at: str
    strategy_readiness_snapshot_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    signal_count: int
    hypothesis_count: int
    analysis_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "strategy_readiness_snapshot_id": self.strategy_readiness_snapshot_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "signal_count": self.signal_count,
            "hypothesis_count": self.hypothesis_count,
            "analysis_count": self.analysis_count,
        }


class StrategyReadinessBenchmark:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> StrategyReadinessBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return StrategyReadinessBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: StrategyReadinessBenchmarkRun,
        snapshot: StrategyReadinessSnapshot,
    ) -> StrategyReadinessBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)
        return StrategyReadinessBenchmarkResult(
            enabled=run.enabled,
            status="STRATEGY_READINESS_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            strategy_readiness_snapshot_id=snapshot.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            signal_count=snapshot.signal_count,
            hypothesis_count=snapshot.hypothesis_count,
            analysis_count=snapshot.analysis_count,
        )
