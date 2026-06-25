"""Storage helpers for ROI crop exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from predixai.vision.roi_crop import ROICrop


@dataclass(frozen=True)
class ROICropExport:
    """Metadata for one exported ROI PNG."""

    roi_id: str
    roi_name: str
    source_frame: str
    output_path: Path
    file_size: int
    image_format: str
    exported_at: str
    reused_source: bool

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "roi_id": self.roi_id,
            "roi_name": self.roi_name,
            "source_frame": self.source_frame,
            "output_path": str(self.output_path),
            "file_size": self.file_size,
            "image_format": self.image_format,
            "exported_at": self.exported_at,
            "reused_source": self.reused_source,
        }


class ROICropStorage:
    """Resolve and prepare storage for ROI crop exports."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def build_output_path(self, roi_crop: ROICrop) -> Path:
        """Build the PNG output path for one ROI crop export."""
        self.output_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roi_{roi_crop.roi_id}_{timestamp}.png"
        return self.output_directory / filename
