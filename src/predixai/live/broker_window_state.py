"""Broker window state metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BrokerWindowState:
    title: str
    resolution_width: int
    resolution_height: int
    left: int
    top: int
    maximized: bool
    foreground: bool
    detected_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "left": self.left,
            "top": self.top,
            "maximized": self.maximized,
            "foreground": self.foreground,
            "detected_at": self.detected_at,
            "metadata": dict(self.metadata),
        }
