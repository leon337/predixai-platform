"""Frame file validation for the Vision Engine foundation."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_HEADER_SIZE = 24


@dataclass(frozen=True)
class FrameValidationResult:
    """Result of validating one frame source file."""

    valid: bool
    errors: tuple[str, ...]
    width: int
    height: int
    image_format: str


class FrameValidator:
    """Validate PNG file metadata without image interpretation."""

    def validate(self, file_path: Path) -> FrameValidationResult:
        """Validate existence, extension, size and PNG dimensions."""
        errors: list[str] = []
        width = 0
        height = 0
        image_format = file_path.suffix.lstrip(".").lower()

        if not file_path.exists():
            errors.append(f"Frame file does not exist: {file_path}")
        elif not file_path.is_file():
            errors.append(f"Frame path is not a file: {file_path}")

        if image_format != "png":
            errors.append("Frame file extension must be PNG.")

        if not errors:
            file_size = file_path.stat().st_size
            if file_size <= 0:
                errors.append("Frame file must not be empty.")
            else:
                width, height = self._read_png_dimensions(file_path, errors)

        return FrameValidationResult(
            valid=not errors,
            errors=tuple(errors),
            width=width,
            height=height,
            image_format=image_format,
        )

    def _read_png_dimensions(
        self,
        file_path: Path,
        errors: list[str],
    ) -> tuple[int, int]:
        header = self._read_png_header(file_path)
        if len(header) < _PNG_HEADER_SIZE:
            errors.append("Frame PNG header is incomplete.")
            return 0, 0

        signature = header[:8]
        ihdr_length = struct.unpack(">I", header[8:12])[0]
        ihdr_type = header[12:16]
        if signature != _PNG_SIGNATURE:
            errors.append("Frame file is not a valid PNG.")
            return 0, 0
        if ihdr_type != b"IHDR" or ihdr_length != 13:
            errors.append("Frame PNG IHDR header is invalid.")
            return 0, 0

        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
        if width <= 0 or height <= 0:
            errors.append("Frame PNG dimensions are invalid.")
            return 0, 0

        return width, height

    def _read_png_header(self, file_path: Path) -> bytes:
        return file_path.read_bytes()[:_PNG_HEADER_SIZE]
