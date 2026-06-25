"""ROI metadata validation."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.vision.roi import RegionOfInterest


@dataclass(frozen=True)
class ROIValidationResult:
    """Result of validating ROI metadata."""

    valid: bool
    errors: tuple[str, ...]


class ROIValidator:
    """Validate ROI metadata without image cropping or pixel reading."""

    def validate(
        self,
        roi: RegionOfInterest,
        frame_width: int,
        frame_height: int,
    ) -> ROIValidationResult:
        """Validate ROI metadata against frame dimensions."""
        errors: list[str] = []

        if not roi.id.strip():
            errors.append("ROI id is required.")
        if not roi.name.strip():
            errors.append("ROI name is required.")
        if roi.x < 0 or roi.y < 0:
            errors.append("ROI coordinates must not be negative.")
        if roi.width <= 0 or roi.height <= 0:
            errors.append("ROI dimensions must be greater than zero.")
        if frame_width <= 0 or frame_height <= 0:
            errors.append("Frame dimensions must be greater than zero.")
        if roi.x + roi.width > frame_width:
            errors.append("ROI width exceeds frame boundary.")
        if roi.y + roi.height > frame_height:
            errors.append("ROI height exceeds frame boundary.")

        return ROIValidationResult(
            valid=not errors,
            errors=tuple(errors),
        )
