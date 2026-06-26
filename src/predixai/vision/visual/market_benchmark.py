"""Market interface benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.market_scene import MarketScene


@dataclass(frozen=True)
class MarketBenchmarkRun:
    """Started benchmark timer for market interface construction."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class MarketBenchmarkResult:
    """Technical benchmark result for market interface construction."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    market_scene_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    element_count: int
    region_count: int
    entity_count: int
    price_region_count: int
    time_region_count: int

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "market_scene_id": self.market_scene_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "element_count": self.element_count,
            "region_count": self.region_count,
            "entity_count": self.entity_count,
            "price_region_count": self.price_region_count,
            "time_region_count": self.time_region_count,
        }


class MarketBenchmark:
    """Measure the deterministic market interface layer."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> MarketBenchmarkRun:
        """Start measuring market interface construction."""
        if self.enabled:
            tracemalloc.start()
        return MarketBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: MarketBenchmarkRun,
        market_scene: MarketScene,
    ) -> MarketBenchmarkResult:
        """Finish measuring and return benchmark metadata."""
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        return MarketBenchmarkResult(
            enabled=run.enabled,
            status="MARKET_SCENE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            market_scene_id=market_scene.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            element_count=market_scene.element_count,
            region_count=market_scene.region_count,
            entity_count=market_scene.entity_count,
            price_region_count=market_scene.price_region_count,
            time_region_count=market_scene.time_region_count,
        )
