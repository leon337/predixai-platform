"""Screen Profile binding for logical regions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from predixai.perception.screen_profile import ScreenProfileRepository


@dataclass(frozen=True)
class RegionProfileBinding:
    """Association between one screen profile and one logical region."""

    profile_id: str
    region_id: str
    enabled: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "profile_id": self.profile_id,
            "region_id": self.region_id,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ScreenProfileBinding:
    """Logical region bindings loaded from a screen profile."""

    profile_id: str
    regions: tuple[RegionProfileBinding, ...]

    @property
    def enabled_region_ids(self) -> tuple[str, ...]:
        """Return enabled region identifiers declared by the profile."""
        return tuple(
            region.region_id
            for region in self.regions
            if region.enabled
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "profile_id": self.profile_id,
            "regions": [region.to_dict() for region in self.regions],
        }


class ProfileBindingLoader:
    """Load region bindings from the configured screen profile."""

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)

    def load(self) -> ScreenProfileBinding:
        """Load logical region bindings from the default profile."""
        profile = ScreenProfileRepository(self.profile_path).load_default()
        return ScreenProfileBinding(
            profile_id=profile.name,
            regions=tuple(
                RegionProfileBinding(
                    profile_id=profile.name,
                    region_id=region.id,
                    enabled=region.enabled,
                    metadata=region.metadata,
                )
                for region in profile.regions
            ),
        )
