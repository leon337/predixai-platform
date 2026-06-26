"""Structured screen layout metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScreenLayoutNode:
    """One node in the deterministic screen layout tree."""

    id: str
    parent_id: str
    node_type: str
    element_id: str
    x: int
    y: int
    width: int
    height: int
    children: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "node_type": self.node_type,
            "element_id": self.element_id,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "children": list(self.children),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ScreenLayout:
    """Screen layout preserving visual positions and hierarchy."""

    id: str
    source_snapshot_id: str
    source_frame: str
    created_at: str
    root_id: str
    nodes: tuple[ScreenLayoutNode, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        """Return the number of layout nodes."""
        return len(self.nodes)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
            "root_id": self.root_id,
            "node_count": self.node_count,
            "nodes": [node.to_dict() for node in self.nodes],
            "metadata": dict(self.metadata),
        }
