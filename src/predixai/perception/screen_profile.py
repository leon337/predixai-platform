"""Screen profile loading for the Perception Engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProfileResolution:
    """Screen profile resolution."""

    width: int
    height: int

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ProfileResolution":
        """Build a profile resolution from JSON values."""
        return cls(width=int(values["width"]), height=int(values["height"]))

    def to_dict(self) -> dict[str, int]:
        """Return a serializable representation."""
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class ScreenProfile:
    """Static screen profile metadata without coordinates."""

    name: str
    resolution: ProfileResolution
    scale_percent: int
    language: str
    theme: str
    broker: str

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ScreenProfile":
        """Build a screen profile from JSON values."""
        return cls(
            name=str(values["name"]),
            resolution=ProfileResolution.from_dict(values["resolution"]),
            scale_percent=int(values["scale_percent"]),
            language=str(values["language"]),
            theme=str(values["theme"]),
            broker=str(values["broker"]),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "name": self.name,
            "resolution": self.resolution.to_dict(),
            "scale_percent": self.scale_percent,
            "language": self.language,
            "theme": self.theme,
            "broker": self.broker,
        }


class ScreenProfileRepository:
    """Load screen profiles from local JSON files."""

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)

    def load_default(self) -> ScreenProfile:
        """Load the default screen profile."""
        with self.profile_path.open("r", encoding="utf-8") as file:
            values = json.load(file)

        if not isinstance(values, dict):
            raise ValueError("Screen profile root must be a JSON object.")
        return ScreenProfile.from_dict(values)
