"""Intelligence benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot


@dataclass(frozen=True)
class IntelligenceBenchmarkRun:
    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class IntelligenceBenchmarkResult:
    enabled: bool
    status: str
    started_at: str
    finished_at: str
    intelligence_snapshot_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    hypothesis_count: int
    analysis_count: int
    entity_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "intelligence_snapshot_id": self.intelligence_snapshot_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "hypothesis_count": self.hypothesis_count,
            "analysis_count": self.analysis_count,
            "entity_count": self.entity_count,
        }


class IntelligenceBenchmark:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> IntelligenceBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return IntelligenceBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: IntelligenceBenchmarkRun,
        intelligence_snapshot: IntelligenceSnapshot,
    ) -> IntelligenceBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)
        return IntelligenceBenchmarkResult(
            enabled=run.enabled,
            status="INTELLIGENCE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            intelligence_snapshot_id=intelligence_snapshot.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            hypothesis_count=intelligence_snapshot.hypothesis_count,
            analysis_count=intelligence_snapshot.analysis_count,
            entity_count=intelligence_snapshot.entity_count,
        )
