"""Pattern analysis benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.pattern_analysis import PatternAnalysis


@dataclass(frozen=True)
class PatternAnalysisBenchmarkRun:
    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class PatternAnalysisBenchmarkResult:
    enabled: bool
    status: str
    started_at: str
    finished_at: str
    pattern_analysis_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    analyzed_pattern_count: int
    classification_count: int
    context_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "pattern_analysis_id": self.pattern_analysis_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "analyzed_pattern_count": self.analyzed_pattern_count,
            "classification_count": self.classification_count,
            "context_count": self.context_count,
        }


class PatternAnalysisBenchmark:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> PatternAnalysisBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return PatternAnalysisBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: PatternAnalysisBenchmarkRun,
        pattern_analysis: PatternAnalysis,
    ) -> PatternAnalysisBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)
        return PatternAnalysisBenchmarkResult(
            enabled=run.enabled,
            status="PATTERN_ANALYSIS_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            pattern_analysis_id=pattern_analysis.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            analyzed_pattern_count=pattern_analysis.pattern_count,
            classification_count=pattern_analysis.classification_count,
            context_count=pattern_analysis.context_count,
        )
