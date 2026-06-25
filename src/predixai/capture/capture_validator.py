"""Capture Engine configuration validation."""

from __future__ import annotations

import os
from dataclasses import dataclass

from predixai.capture.capture_storage import CaptureStorage


@dataclass(frozen=True)
class CaptureValidationResult:
    """Result of Capture Engine validation."""

    valid: bool
    errors: tuple[str, ...]


class CaptureValidator:
    """Validate only the technical requirements allowed by PTP-005."""

    def validate(self, storage: CaptureStorage) -> CaptureValidationResult:
        """Validate output directory, write permission and PNG format."""
        errors: list[str] = []

        if not storage.output_directory.exists():
            errors.append(
                f"Capture directory does not exist: {storage.output_directory}"
            )
        elif not storage.output_directory.is_dir():
            errors.append(
                f"Capture output path is not a directory: "
                f"{storage.output_directory}"
            )
        elif not os.access(storage.output_directory, os.W_OK):
            errors.append(
                f"Capture directory is not writable: {storage.output_directory}"
            )

        if storage.image_format != "png":
            errors.append("Capture image format must be PNG.")

        return CaptureValidationResult(
            valid=not errors,
            errors=tuple(errors),
        )
