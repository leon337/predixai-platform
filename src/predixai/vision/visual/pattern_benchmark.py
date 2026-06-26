"""Pattern benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.pattern_scene import PatternScene


@dataclass(frozen=True)
class PatternBenchmarkRun:
    """Started benchmark timer for pattern detection."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class PatternBenchmarkResult:
    """Technical benchmark result for pattern detection."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    pattern_scene_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    pattern_count: int
    entity_count: int
    region_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "pattern_scene_id": self.pattern_scene_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "pattern_count": self.pattern_count,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
        }


class PatternBenchmark:
    """Measure the deterministic pattern layer."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> PatternBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return PatternBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: PatternBenchmarkRun,
        pattern_scene: PatternScene,
    ) -> PatternBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        return PatternBenchmarkResult(
            enabled=run.enabled,
            status="PATTERN_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            pattern_scene_id=pattern_scene.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            pattern_count=pattern_scene.pattern_count,
            entity_count=pattern_scene.entity_count,
            region_count=pattern_scene.region_count,
        )
