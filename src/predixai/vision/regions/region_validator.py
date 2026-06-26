"""Logical region metadata validation."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.vision.regions.region import Region
from predixai.vision.regions.region_registry import RegionRegistry


@dataclass(frozen=True)
class RegionValidationResult:
    """Result of validating region metadata."""

    valid: bool
    errors: tuple[str, ...]
    valid_region_count: int = 0


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
            valid_region_count=1 if not errors else 0,
        )

    def validate_registry(
        self,
        registry: RegionRegistry,
        frame_width: int,
        frame_height: int,
    ) -> RegionValidationResult:
        """Validate all regions and detect duplicate identifiers."""
        errors: list[str] = []
        seen_ids: set[str] = set()
        valid_region_count = 0

        if not registry.enabled:
            errors.append("Region registry is disabled.")

        for region in registry.regions:
            if region.id in seen_ids:
                errors.append(f"Duplicate region id: {region.id}")
                continue
            seen_ids.add(region.id)

            validation = self.validate(region, frame_width, frame_height)
            errors.extend(validation.errors)
            if validation.valid:
                valid_region_count += 1

        return RegionValidationResult(
            valid=not errors,
            errors=tuple(errors),
            valid_region_count=valid_region_count,
        )
