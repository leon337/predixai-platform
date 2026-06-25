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
        if roi.x + roi.width > image_buffer.width:
            errors.append(f"ROI exceeds image width: {roi.id}")
        if roi.y + roi.height > image_buffer.height:
            errors.append(f"ROI exceeds image height: {roi.id}")

        return ROICropValidationResult(valid=not errors, errors=tuple(errors))
