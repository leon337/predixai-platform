"""Capture storage configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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

    def build_snapshot_path(self, captured_at: datetime) -> Path:
        """Build a unique path for one manual snapshot."""
        timestamp = captured_at.strftime("%Y%m%d_%H%M%S")
        base_path = self.output_directory / (
            f"capture_{timestamp}.{self.image_format}"
        )
        if not base_path.exists():
            return base_path

        for index in range(1, 1000):
            candidate = self.output_directory / (
                f"capture_{timestamp}_{index:03d}.{self.image_format}"
            )
            if not candidate.exists():
                return candidate

        raise RuntimeError("Unable to build a unique manual snapshot path.")
