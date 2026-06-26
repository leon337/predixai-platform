"""Structural signal metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot


@dataclass(frozen=True)
class Signal:
    id: str
    source_intelligence_snapshot_id: str
    source_market_structure_id: str
    source_pattern_analysis_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    signal_type: str
    description: str
    strength: float
    intelligence_snapshot: IntelligenceSnapshot
    metadata: dict[str, Any] = field(default_factory=dict)

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
            "signal_type": self.signal_type,
            "description": self.description,
            "strength": self.strength,
            "intelligence_snapshot": self.intelligence_snapshot.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Signals:
    source_intelligence_snapshot_id: str
    source_market_structure_id: str
    source_pattern_analysis_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    signals: tuple[Signal, ...]

    @property
    def count(self) -> int:
        return len(self.signals)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_intelligence_snapshot_id": self.source_intelligence_snapshot_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_pattern_analysis_id": self.source_pattern_analysis_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "signals": [item.to_dict() for item in self.signals],
        }
