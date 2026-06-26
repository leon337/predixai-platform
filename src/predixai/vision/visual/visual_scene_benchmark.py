"""Visual scene benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from predixai.vision.visual.visual_scene import VisualScene


@dataclass(frozen=True)
class VisualSceneBenchmarkRun:
    """Started benchmark timer for visual scene construction."""

    started_at: str
    start_counter: float
    enabled: bool


@dataclass(frozen=True)
class VisualSceneBenchmarkResult:
    """Technical benchmark result for visual scene construction."""

    enabled: bool
    status: str
    started_at: str
    finished_at: str
    visual_scene_id: str
    processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    object_count: int
    element_count: int
    region_count: int
    layout_node_count: int

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "enabled": self.enabled,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "visual_scene_id": self.visual_scene_id,
            "processing_time_ms": self.processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "object_count": self.object_count,
            "element_count": self.element_count,
            "region_count": self.region_count,
            "layout_node_count": self.layout_node_count,
        }


class VisualSceneBenchmark:
    """Measure the visual scene construction layer."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def start(self) -> VisualSceneBenchmarkRun:
        """Start measuring visual scene construction."""
        if self.enabled:
            tracemalloc.start()
        return VisualSceneBenchmarkRun(
            started_at=datetime.now().astimezone().isoformat(),
            start_counter=perf_counter(),
            enabled=self.enabled,
        )

    def finish(
        self,
        run: VisualSceneBenchmarkRun,
        visual_scene: VisualScene,
    ) -> VisualSceneBenchmarkResult:
        """Finish measuring and return benchmark metadata."""
        processing_time_ms = round((perf_counter() - run.start_counter) * 1000, 3)
        current_memory_kb = 0.0
        peak_memory_kb = 0.0
        if run.enabled:
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            current_memory_kb = round(current_memory / 1024, 3)
            peak_memory_kb = round(peak_memory / 1024, 3)

        return VisualSceneBenchmarkResult(
            enabled=run.enabled,
            status="VISUAL_SCENE_COMPLETED",
            started_at=run.started_at,
            finished_at=datetime.now().astimezone().isoformat(),
            visual_scene_id=visual_scene.id,
            processing_time_ms=processing_time_ms,
            peak_memory_kb=peak_memory_kb,
            current_memory_kb=current_memory_kb,
            object_count=visual_scene.object_count,
            element_count=visual_scene.element_count,
            region_count=visual_scene.region_count,
            layout_node_count=visual_scene.layout.node_count,
        )
