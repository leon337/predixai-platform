"""PNG byte validation for the Image Loader foundation."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_HEADER_SIZE = 24


@dataclass(frozen=True)
class ImageLoaderValidationResult:
    """Result of validating PNG bytes loaded from a file."""

    valid: bool
    errors: tuple[str, ...]
    width: int
    height: int
    image_format: str


class ImageLoaderValidator:
    """Validate PNG file bytes without decoding image pixels."""

    def validate(
        self,
        file_path: Path,
        image_bytes: bytes,
    ) -> ImageLoaderValidationResult:
        """Validate existence, PNG extension, size and header dimensions."""
        errors: list[str] = []
        width = 0
        height = 0
        image_format = file_path.suffix.lstrip(".").lower()

        if not file_path.exists():
            errors.append(f"Image file does not exist: {file_path}")
        elif not file_path.is_file():
            errors.append(f"Image path is not a file: {file_path}")

        if image_format != "png":
            errors.append("Image file extension must be PNG.")

        if not image_bytes:
            errors.append("Image file bytes must not be empty.")

        if not errors:
            width, height = self._read_png_dimensions(image_bytes, errors)

        return ImageLoaderValidationResult(
            valid=not errors,
            errors=tuple(errors),
            width=width,
            height=height,
            image_format=image_format,
        )

    def _read_png_dimensions(
        self,
        image_bytes: bytes,
        errors: list[str],
    ) -> tuple[int, int]:
        header = image_bytes[:_PNG_HEADER_SIZE]
        if len(header) < _PNG_HEADER_SIZE:
            errors.append("Image PNG header is incomplete.")
            return 0, 0

        signature = header[:8]
        ihdr_length = struct.unpack(">I", header[8:12])[0]
        ihdr_type = header[12:16]
        if signature != _PNG_SIGNATURE:
            errors.append("Image file is not a valid PNG.")
            return 0, 0
        if ihdr_type != b"IHDR" or ihdr_length != 13:
            errors.append("Image PNG IHDR header is invalid.")
            return 0, 0

        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
        if width <= 0 or height <= 0:
            errors.append("Image PNG dimensions are invalid.")
            return 0, 0

        return width, height
