"""Unified visual scene metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.screen_layout import ScreenLayout
from predixai.vision.visual.screen_object import ScreenObjectRegistry
from predixai.vision.visual.visual_snapshot import VisualSnapshot


@dataclass(frozen=True)
class VisualScene:
    """Unified representation of a captured screen scene."""

    id: str
    source_snapshot_id: str
    source_frame: str
    frame_sha256: str
    created_at: str
    visual_snapshot: VisualSnapshot
    layout: ScreenLayout
    object_registry: ScreenObjectRegistry
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def region_count(self) -> int:
        """Return the number of structured regions."""
        return self.visual_snapshot.structured_ocr.total_regions

    @property
    def element_count(self) -> int:
        """Return the number of layout elements."""
        return int(self.metadata.get("element_count", 0))

    @property
    def object_count(self) -> int:
        """Return the number of registered objects."""
        return self.object_registry.count

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_frame": self.source_frame,
            "frame_sha256": self.frame_sha256,
            "created_at": self.created_at,
            "visual_snapshot": self.visual_snapshot.to_dict(),
            "structured_ocr": self.visual_snapshot.structured_ocr.to_dict(),
            "layout": self.layout.to_dict(),
            "object_registry": self.object_registry.to_dict(),
            "region_count": self.region_count,
            "element_count": self.element_count,
            "object_count": self.object_count,
            "metadata": dict(self.metadata),
        }
