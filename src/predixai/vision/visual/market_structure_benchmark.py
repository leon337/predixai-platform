"""Market structure benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.market_structure import MarketStructure


@dataclass(frozen=True)
class MarketStructureBenchmarkRun:
    """Started benchmark timer for market structure construction."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class MarketStructureBenchmarkResult:
    """Technical benchmark result for market structure construction."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    market_structure_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    entity_count: int
    region_count: int
    element_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "market_structure_id": self.market_structure_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "element_count": self.element_count,
        }


class MarketStructureBenchmark:
    """Measure the deterministic market structure layer."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> MarketStructureBenchmarkRun:
        if self.enabled:
            tracemalloc.start()
        return MarketStructureBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: MarketStructureBenchmarkRun,
        market_structure: MarketStructure,
    ) -> MarketStructureBenchmarkResult:
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        return MarketStructureBenchmarkResult(
            enabled=run.enabled,
            status="MARKET_STRUCTURE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            market_structure_id=market_structure.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            entity_count=market_structure.entity_count,
            region_count=market_structure.region_count,
            element_count=market_structure.element_count,
        )
