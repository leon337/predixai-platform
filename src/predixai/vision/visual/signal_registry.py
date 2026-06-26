"""Registry for structural signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.signal import Signal


@dataclass(frozen=True)
class SignalRegistry:
    id: str
    source_intelligence_snapshot_id: str
    source_market_structure_id: str
    source_pattern_analysis_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    signals: tuple[Signal, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.signals)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_intelligence_snapshot_id": self.source_intelligence_snapshot_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "signals": [signal.to_dict() for signal in self.signals],
            "metadata": dict(self.metadata),
        }
