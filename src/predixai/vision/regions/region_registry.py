"""Region registry for logical screen mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.regions.region import Region


@dataclass(frozen=True)
class RegionRegistry:
    """Immutable registry of logical region metadata."""

    version: str = "1.0"
    enabled: bool = True
    profile_id: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    regions: tuple[Region, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        """Return the number of registered regions."""
        return len(self.regions)

    def register(self, region: Region) -> "RegionRegistry":
        """Return a new registry with one region added."""
        if any(existing.id == region.id for existing in self.regions):
            raise ValueError(f"Region already registered: {region.id}")
        return RegionRegistry(
            version=self.version,
            enabled=self.enabled,
            profile_id=self.profile_id,
            metadata=dict(self.metadata),
            regions=(*self.regions, region),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "version": self.version,
            "enabled": self.enabled,
            "profile_id": self.profile_id,
            "metadata": dict(self.metadata),
            "count": self.count,
            "regions": [region.to_dict() for region in self.regions],
        }
