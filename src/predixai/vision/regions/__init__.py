"""Logical region mapping foundation."""

from predixai.vision.regions.profile_binding import (
    ProfileBindingLoader,
    RegionProfileBinding,
    ScreenProfileBinding,
)
from predixai.vision.regions.region import Region
from predixai.vision.regions.region_manager import RegionManager
from predixai.vision.regions.region_registry import RegionRegistry
from predixai.vision.regions.region_validator import (
    RegionValidationResult,
    RegionValidator,
)

__all__ = [
    "ProfileBindingLoader",
    "Region",
    "RegionManager",
    "RegionProfileBinding",
    "RegionRegistry",
    "RegionValidationResult",
    "RegionValidator",
    "ScreenProfileBinding",
]
