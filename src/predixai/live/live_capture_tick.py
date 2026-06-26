"""Live capture tick metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveCaptureTick:
    tick_index: int
    captured_at: str
    capture_path: str
    window_title: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "tick_index": self.tick_index,
            "captured_at": self.captured_at,
            "capture_path": self.capture_path,
            "window_title": self.window_title,
            "metadata": dict(self.metadata),
        }
