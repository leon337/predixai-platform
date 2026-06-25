"""Region of Interest metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegionOfInterest:
    """Metadata for one future screen region."""

    id: str
    name: str
    description: str
    x: int
    y: int
    width: int
    height: int
    enabled: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
