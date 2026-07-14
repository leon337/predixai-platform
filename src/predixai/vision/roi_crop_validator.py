"""ROI crop validation without pixel access."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.roi import RegionOfInterest


@dataclass(frozen=True)
class ROICropValidationResult:
    """Result of validating ROI coordinates against image bounds."""

    valid: bool
    errors: tuple[str, ...]


class ROICropValidator:
    """Validate ROI metadata using only image dimensions."""

    def validate(
        self,
        roi: RegionOfInterest,
        image_buffer: ImageBuffer,
    ) -> ROICropValidationResult:
        """Validate that ROI coordinates fit inside the source image."""
        return self.validate_dimensions(
            roi=roi,
            image_width=image_buffer.width,
            image_height=image_buffer.height,
        )

    def validate_dimensions(
        self,
        *,
        roi: RegionOfInterest,
        image_width: int,
        image_height: int,
    ) -> ROICropValidationResult:
        """Validate a region against explicit in-memory frame dimensions."""
        errors: list[str] = []

        if not roi.enabled:
            errors.append(f"ROI is disabled: {roi.id}")
        if roi.x < 0:
            errors.append(f"ROI x must be greater than or equal to zero: {roi.id}")
        if roi.y < 0:
            errors.append(f"ROI y must be greater than or equal to zero: {roi.id}")
        if roi.width <= 0:
            errors.append(f"ROI width must be greater than zero: {roi.id}")
        if roi.height <= 0:
            errors.append(f"ROI height must be greater than zero: {roi.id}")
        if image_width <= 0 or image_height <= 0:
            errors.append("Source image dimensions must be positive")
        if roi.x + roi.width > image_width:
            errors.append(f"ROI exceeds image width: {roi.id}")
        if roi.y + roi.height > image_height:
            errors.append(f"ROI exceeds image height: {roi.id}")

        return ROICropValidationResult(valid=not errors, errors=tuple(errors))
