"""Semantic pipeline benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.semantic_registry import SemanticRegistry
from predixai.vision.visual.semantic_scene import SemanticScene


@dataclass(frozen=True)
class SemanticBenchmarkRun:
    """Started benchmark timer for semantic construction."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class SemanticBenchmarkResult:
    """Technical benchmark result for semantic construction."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    semantic_scene_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    entity_count: int
    label_count: int
    region_count: int

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "semantic_scene_id": self.semantic_scene_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "entity_count": self.entity_count,
            "label_count": self.label_count,
            "region_count": self.region_count,
        }


class SemanticBenchmark:
    """Measure the deterministic semantic construction layer."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> SemanticBenchmarkRun:
        """Start measuring semantic construction."""
        if self.enabled:
            tracemalloc.start()
        return SemanticBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: SemanticBenchmarkRun,
        semantic_scene: SemanticScene,
        semantic_registry: SemanticRegistry,
    ) -> SemanticBenchmarkResult:
        """Finish measuring and return benchmark metadata."""
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        return SemanticBenchmarkResult(
            enabled=run.enabled,
            status="SEMANTIC_SCENE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            semantic_scene_id=semantic_scene.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            entity_count=semantic_registry.count,
            label_count=semantic_registry.label_count,
            region_count=semantic_scene.region_count,
        )
