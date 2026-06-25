"""ROI Manager foundation."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.frame import Frame
from predixai.vision.roi import RegionOfInterest
from predixai.vision.roi_registry import ROIRegistry
from predixai.vision.roi_validator import ROIValidator

FULL_SCREEN_ROI_ID = "FULL_SCREEN"


class ROIManager:
    """Registers future screen regions as metadata only."""

    def __init__(self) -> None:
        self.validator = ROIValidator()

    def load_default_registry(self, frame: Frame) -> ROIRegistry:
        """Create a registry containing only the FULL_SCREEN ROI."""
        timestamp = datetime.now().astimezone().isoformat()
        full_screen = RegionOfInterest(
            id=FULL_SCREEN_ROI_ID,
            name="Full Screen",
            description="Full capture area reserved for future Vision steps.",
            x=0,
            y=0,
            width=frame.width,
            height=frame.height,
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
        )

        validation = self.validator.validate(
            roi=full_screen,
            frame_width=frame.width,
            frame_height=frame.height,
        )
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return ROIRegistry().register(full_screen)
