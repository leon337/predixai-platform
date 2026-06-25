"""Capture storage configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from predixai.core.config import AppConfig


@dataclass(frozen=True)
class CaptureStorage:
    """Defines where future screenshots will be stored."""

    output_directory: Path
    image_format: str
    compression: int
    max_history: int

    @classmethod
    def from_config(cls, config: AppConfig) -> "CaptureStorage":
        """Create storage metadata from application config."""
        capture_config = config.capture
        return cls(
            output_directory=config.resolve_project_path(
                str(capture_config["output_directory"])
            ),
            image_format=str(capture_config["image_format"]).lower(),
            compression=int(capture_config["compression"]),
            max_history=int(capture_config["max_history"]),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "output_directory": str(self.output_directory),
            "image_format": self.image_format,
            "compression": self.compression,
            "max_history": self.max_history,
        }
