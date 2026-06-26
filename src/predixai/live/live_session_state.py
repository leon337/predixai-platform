"""Live session state metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveSessionState:
    state: str
    started_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }
