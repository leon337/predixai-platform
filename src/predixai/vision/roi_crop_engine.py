"""ROI Crop Engine foundation."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.roi import RegionOfInterest
from predixai.vision.roi_crop import ROICrop
from predixai.vision.roi_crop_validator import ROICropValidator
from predixai.vision.roi_registry import ROIRegistry


class ROICropEngine:
    """Create ROI crop metadata without extracting image content."""

    def __init__(self) -> None:
        self.validator = ROICropValidator()

    def create_crop(
        self,
        roi: RegionOfInterest,
        image_buffer: ImageBuffer,
    ) -> ROICrop:
        """Create one ROI crop metadata object from validated coordinates."""
        validation = self.validator.validate(roi, image_buffer)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return ROICrop(
            roi_id=roi.id,
            roi_name=roi.name,
            x=roi.x,
            y=roi.y,
            width=roi.width,
            height=roi.height,
            source_frame=image_buffer.filename,
            created_at=datetime.now().astimezone().isoformat(),
        )

    def create_crops(
        self,
        registry: ROIRegistry,
        image_buffer: ImageBuffer,
    ) -> tuple[ROICrop, ...]:
        """Create ROI crop metadata for all registered ROIs."""
        return tuple(
            self.create_crop(roi, image_buffer)
            for roi in registry.rois
        )
