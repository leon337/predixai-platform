"""ROI registry for Vision metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from predixai.vision.roi import RegionOfInterest


@dataclass(frozen=True)
class ROIRegistry:
    """Immutable registry of ROI metadata."""

    rois: tuple[RegionOfInterest, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        """Return the number of registered ROIs."""
        return len(self.rois)

    def register(self, roi: RegionOfInterest) -> "ROIRegistry":
        """Return a new registry with one ROI added."""
        if any(existing.id == roi.id for existing in self.rois):
            raise ValueError(f"ROI already registered: {roi.id}")
        return ROIRegistry(rois=(*self.rois, roi))

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "count": self.count,
            "rois": [roi.to_dict() for roi in self.rois],
        }
