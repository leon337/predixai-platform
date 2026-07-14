"""Region of Interest metadata."""

from __future__ import annotations

from dataclasses import dataclass
import math


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


@dataclass(frozen=True)
class RelativeRegionGeometry:
    """Resolution-independent geometry for one authorized client region."""

    x_ratio: float
    y_ratio: float
    width_ratio: float
    height_ratio: float

    def __post_init__(self) -> None:
        values = (
            self.x_ratio,
            self.y_ratio,
            self.width_ratio,
            self.height_ratio,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("relative region ratios must be finite")
        if self.x_ratio < 0 or self.y_ratio < 0:
            raise ValueError("relative region origin must not be negative")
        if self.width_ratio <= 0 or self.height_ratio <= 0:
            raise ValueError("relative region dimensions must be positive")
        if self.x_ratio + self.width_ratio > 1.0 + 1e-12:
            raise ValueError("relative region exceeds the client width")
        if self.y_ratio + self.height_ratio > 1.0 + 1e-12:
            raise ValueError("relative region exceeds the client height")

    @classmethod
    def from_pixels(
        cls,
        *,
        x: int,
        y: int,
        width: int,
        height: int,
        window_width: int,
        window_height: int,
    ) -> "RelativeRegionGeometry":
        """Create exact relative geometry from a user-selected pixel box."""
        if window_width <= 0 or window_height <= 0:
            raise ValueError("authorized client dimensions must be positive")
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("selected pixel geometry is invalid")
        if x + width > window_width or y + height > window_height:
            raise ValueError("selected pixel geometry exceeds the authorized client")
        return cls(
            x_ratio=x / window_width,
            y_ratio=y / window_height,
            width_ratio=width / window_width,
            height_ratio=height / window_height,
        )

    def to_pixels(self, *, window_width: int, window_height: int) -> tuple[int, int, int, int]:
        """Resolve ratios without silently clamping an invalid region."""
        if window_width <= 0 or window_height <= 0:
            raise ValueError("authorized client dimensions must be positive")
        x = round(self.x_ratio * window_width)
        y = round(self.y_ratio * window_height)
        right = round((self.x_ratio + self.width_ratio) * window_width)
        bottom = round((self.y_ratio + self.height_ratio) * window_height)
        width = right - x
        height = bottom - y
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("resolved pixel geometry is invalid")
        if right > window_width or bottom > window_height:
            raise ValueError("resolved pixel geometry exceeds the authorized client")
        return x, y, width, height

    def to_dict(self) -> dict[str, float]:
        return {
            "x_ratio": self.x_ratio,
            "y_ratio": self.y_ratio,
            "width_ratio": self.width_ratio,
            "height_ratio": self.height_ratio,
        }
