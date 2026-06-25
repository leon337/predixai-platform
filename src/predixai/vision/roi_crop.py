"""ROI crop metadata for future visual processing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ROICrop:
    """Mathematical ROI crop metadata without pixel extraction."""

    roi_id: str
    roi_name: str
    x: int
    y: int
    width: int
    height: int
    source_frame: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
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
