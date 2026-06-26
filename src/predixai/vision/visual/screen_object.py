"""Reusable screen object metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScreenObject:
    """Registered object derived from one screen element."""

    id: str
    stable_key: str
    element_id: str
    object_type: str
    x: int
    y: int
    width: int
    height: int
    first_seen_snapshot_id: str
    last_seen_snapshot_id: str
    observation_count: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "stable_key": self.stable_key,
            "element_id": self.element_id,
            "object_type": self.object_type,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "first_seen_snapshot_id": self.first_seen_snapshot_id,
            "last_seen_snapshot_id": self.last_seen_snapshot_id,
            "observation_count": self.observation_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ScreenObjectRegistry:
    """Registry of screen objects for one visual snapshot."""

    id: str
    source_snapshot_id: str
    source_frame: str
    created_at: str
    objects: tuple[ScreenObject, ...]

    @property
    def count(self) -> int:
        """Return the number of registered objects."""
        return len(self.objects)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "count": self.count,
            "objects": [screen_object.to_dict() for screen_object in self.objects],
        }
