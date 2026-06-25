"""Foundation event registry for Core startup events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class SystemEvent:
    """A technical event emitted by the foundation."""

    name: str
    payload: Mapping[str, Any]
    created_at: str


class EventRegistry:
    """In-memory registry for startup events."""

    def __init__(self) -> None:
        self._events: list[SystemEvent] = []

    def record(
        self,
        name: str,
        payload: Mapping[str, Any] | None = None,
    ) -> SystemEvent:
        """Record a technical event and return it."""
        event = SystemEvent(
            name=name,
            payload=dict(payload or {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._events.append(event)
        return event

    def all(self) -> tuple[SystemEvent, ...]:
        """Return all recorded technical events."""
        return tuple(self._events)
