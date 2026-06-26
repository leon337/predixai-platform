"""Pattern analysis metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.pattern_scene import PatternScene


@dataclass(frozen=True)
class PatternAnalysis:
    id: str
    source_pattern_scene_id: str
    source_market_structure_id: str
    source_market_scene_id: str
    source_visual_scene_id: str
    source_frame: str
    created_at: str
    pattern_scene: PatternScene
    classifications: tuple[dict[str, object], ...]
    contexts: tuple[dict[str, object], ...]
    analysis_results: tuple[dict[str, object], ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pattern_count(self) -> int:
        return self.pattern_scene.pattern_count

    @property
    def classification_count(self) -> int:
        return len(self.classifications)

    @property
    def context_count(self) -> int:
        return len(self.contexts)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_pattern_scene_id": self.source_pattern_scene_id,
            "source_market_structure_id": self.source_market_structure_id,
            "source_market_scene_id": self.source_market_scene_id,
            "source_visual_scene_id": self.source_visual_scene_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "pattern_scene": self.pattern_scene.to_dict(),
            "classifications": [dict(item) for item in self.classifications],
            "contexts": [dict(item) for item in self.contexts],
            "analysis_results": [dict(item) for item in self.analysis_results],
            "pattern_count": self.pattern_count,
            "classification_count": self.classification_count,
            "context_count": self.context_count,
            "metadata": dict(self.metadata),
        }
