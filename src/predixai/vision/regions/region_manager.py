"""Region Mapping foundation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from predixai.vision.frame import Frame
from predixai.vision.regions.profile_binding import ProfileBindingLoader
from predixai.vision.regions.region import Region
from predixai.vision.regions.region_registry import RegionRegistry
from predixai.vision.regions.region_validator import RegionValidator

FULL_SCREEN_REGION_ID = "FULL_SCREEN"


class RegionManager:
    """Registers logical screen regions as metadata only."""

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)
        self.binding_loader = ProfileBindingLoader(self.profile_path)
        self.validator = RegionValidator()

    def load_default_registry(self, frame: Frame) -> RegionRegistry:
        """Create a registry containing only the FULL_SCREEN region."""
        binding = self.binding_loader.load()
        full_screen = Region(
            id=FULL_SCREEN_REGION_ID,
            name="Full Screen",
            description="Full capture area reserved for future region mapping.",
            x=0,
            y=0,
            width=frame.width,
            height=frame.height,
            enabled=True,
            created_at=datetime.now().astimezone().isoformat(),
        )

        registry = RegionRegistry(
            version="1.0",
            enabled=True,
            profile_id=binding.profile_id,
            metadata={"screen_profile_binding": binding.to_dict()},
        ).register(full_screen)

        validation = self.validator.validate_registry(
            registry=registry,
            frame_width=frame.width,
            frame_height=frame.height,
        )
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return registry
