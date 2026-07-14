"""ROI crop metadata."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ROICrop:
    roi_id: str
    roi_name: str
    x: int
    y: int
    width: int
    height: int
    source_frame: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "roi_id": self.roi_id,
            "roi_name": self.roi_name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "source_frame": self.source_frame,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RGB24Crop:
    """Immutable in-memory RGB24 crop with verified hash."""

    roi_id: str
    x: int
    y: int
    width: int
    height: int
    sha256: str
    pixel_format: str = "RGB24"
    pixel_bytes: bytes = field(default=b"", repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.roi_id.strip():
            raise ValueError("crop region id is required")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("crop dimensions must be positive")
        if self.pixel_format != "RGB24":
            raise ValueError("crop pixel format must be RGB24")
        if len(self.pixel_bytes) != self.width * self.height * 3:
            raise ValueError(
                "RGB24 crop byte count contradicts its dimensions"
            )
        expected_hash = hashlib.sha256(self.pixel_bytes).hexdigest()
        if self.sha256 != expected_hash:
            raise ValueError("RGB24 crop SHA256 contradicts its pixels")

    def to_dict(self) -> dict[str, object]:
        return {
            "REGION_ID": self.roi_id,
            "PIXEL_GEOMETRY": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "PIXEL_FORMAT": self.pixel_format,
            "PIXEL_SHA256": self.sha256,
        }
