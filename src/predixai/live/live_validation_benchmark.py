"""Live validation benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.live.live_validation_report import LiveValidationReport


@dataclass(frozen=True)
class LiveValidationBenchmarkRun:
    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class LiveValidationBenchmarkResult:
    enabled: bool
    status: str
    started_at: str
    finished_at: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    total_captures: int
    detected_fields: int
    unknown_fields: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "total_captures": self.total_captures,
            "detected_fields": self.detected_fields,
            "unknown_fields": self.unknown_fields,
        }


class LiveValidationBenchmark:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> LiveValidationBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return LiveValidationBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: LiveValidationBenchmarkRun,
        report: LiveValidationReport,
    ) -> LiveValidationBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)
        return LiveValidationBenchmarkResult(
            enabled=run.enabled,
            status="LIVE_VALIDATION_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            total_captures=report.total_captures,
            detected_fields=len(report.fields_detected),
            unknown_fields=len(report.unknown_fields),
        )
