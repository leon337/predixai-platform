"""Visual pipeline benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.ocr import OCRResult
from predixai.vision.visual.visual_snapshot import VisualSnapshot


@dataclass(frozen=True)
class VisualBenchmarkRun:
    """Started benchmark timer for the visual structured pipeline."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class VisualBenchmarkResult:
    """Technical benchmark result for the visual structured pipeline."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    visual_snapshot_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    region_count: int
    block_count: int
    text_length: int
    ocr_cache_hits: tuple[bool, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "visual_snapshot_id": self.visual_snapshot_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "region_count": self.region_count,
            "block_count": self.block_count,
            "text_length": self.text_length,
            "ocr_cache_hits": list(self.ocr_cache_hits),
        }


class VisualBenchmark:
    """Measure the structured visual pipeline."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> VisualBenchmarkRun:
        """Start measuring the structured visual pipeline."""
        if self.enabled:
            tracemalloc.start()
        return VisualBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: VisualBenchmarkRun,
        visual_snapshot: VisualSnapshot,
        ocr_results: tuple[OCRResult, ...],
    ) -> VisualBenchmarkResult:
        """Finish measuring and return benchmark metadata."""
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        structured_ocr = visual_snapshot.structured_ocr
        return VisualBenchmarkResult(
            enabled=run.enabled,
            status="VISUAL_PIPELINE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            visual_snapshot_id=visual_snapshot.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            region_count=structured_ocr.total_regions,
            block_count=structured_ocr.total_blocks,
            text_length=len(structured_ocr.combined_text),
            ocr_cache_hits=tuple(ocr_result.cache_hit for ocr_result in ocr_results),
        )
