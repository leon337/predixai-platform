"""Logical region metadata validation."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.vision.regions.region import Region


@dataclass(frozen=True)
class RegionValidationResult:
    """Result of validating region metadata."""

    valid: bool
    errors: tuple[str, ...]


class RegionValidator:
    """Validate logical regions using only frame dimensions."""

    def validate(
        self,
        region: Region,
        frame_width: int,
        frame_height: int,
    ) -> RegionValidationResult:
        """Validate region metadata against frame dimensions."""
        errors: list[str] = []

        if not region.id.strip():
            errors.append("Region id is required.")
        if not region.name.strip():
            errors.append("Region name is required.")
        if region.x < 0 or region.y < 0:
            errors.append("Region coordinates must not be negative.")
        if region.width <= 0 or region.height <= 0:
            errors.append("Region dimensions must be greater than zero.")
        if frame_width <= 0 or frame_height <= 0:
            errors.append("Frame dimensions must be greater than zero.")
        if region.x + region.width > frame_width:
            errors.append("Region width exceeds frame boundary.")
        if region.y + region.height > frame_height:
            errors.append("Region height exceeds frame boundary.")

        return RegionValidationResult(
            valid=not errors,
            errors=tuple(errors),
        )
