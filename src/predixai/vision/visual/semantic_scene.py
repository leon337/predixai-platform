"""Unified deterministic semantic scene."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.semantic_element import SemanticElements
from predixai.vision.visual.semantic_label import SemanticLabelMapping
from predixai.vision.visual.visual_scene import VisualScene


@dataclass(frozen=True)
class SemanticScene:
    """Semantic representation of a visual scene without decision-making."""

    id: str
    source_scene_id: str
    source_frame: str
    frame_sha256: str
    created_at: str
    visual_scene: VisualScene
    semantic_elements: SemanticElements
    label_mapping: SemanticLabelMapping
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def entity_count(self) -> int:
        """Return the number of semantic entities."""
        return self.semantic_elements.count

    @property
    def label_count(self) -> int:
        """Return the number of semantic labels."""
        return self.label_mapping.count

    @property
    def region_count(self) -> int:
        """Return the number of semantic regions."""
        return self.semantic_elements.region_count

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_scene_id": self.source_scene_id,
            "source_frame": self.source_frame,
            "frame_sha256": self.frame_sha256,
            "created_at": self.created_at,
            "visual_scene": self.visual_scene.to_dict(),
            "semantic_elements": self.semantic_elements.to_dict(),
            "label_mapping": self.label_mapping.to_dict(),
            "entity_count": self.entity_count,
            "label_count": self.label_count,
            "region_count": self.region_count,
            "metadata": dict(self.metadata),
        }
