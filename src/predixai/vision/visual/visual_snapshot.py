"""Visual snapshot metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.structured_ocr_result import StructuredOCRResult


@dataclass(frozen=True)
class VisualSnapshot:
    """Complete structured visual snapshot for one screen capture."""

    id: str
    session_id: str
    captured_at: str
    created_at: str
    source_frame: str
    frame_sha256: str
    width: int
    height: int
    structured_ocr: StructuredOCRResult
    regions: dict[str, object]
    roi_exports: tuple[dict[str, object], ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "captured_at": self.captured_at,
            "created_at": self.created_at,
            "source_frame": self.source_frame,
            "frame_sha256": self.frame_sha256,
            "width": self.width,
            "height": self.height,
            "structured_ocr": self.structured_ocr.to_dict(),
            "regions": dict(self.regions),
            "roi_exports": [dict(roi_export) for roi_export in self.roi_exports],
            "metadata": dict(self.metadata),
        }
