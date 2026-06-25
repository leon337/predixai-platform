"""OCR image validation for the foundation phase."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class OCRValidationResult:
    """Result of validating an OCR input image."""

    valid: bool
    errors: tuple[str, ...]
    image_format: str
    file_size: int


class OCRValidator:
    """Validate a PNG image path without reading text or pixels."""

    def validate(self, image_path: Path) -> OCRValidationResult:
        """Validate existence, extension, size and PNG signature."""
        errors: list[str] = []
        image_format = image_path.suffix.lstrip(".").lower()
        file_size = 0

        if not image_path.exists():
            errors.append(f"OCR image does not exist: {image_path}")
        elif not image_path.is_file():
            errors.append(f"OCR image path is not a file: {image_path}")

        if image_format != "png":
            errors.append("OCR image extension must be PNG.")

        if not errors:
            file_size = image_path.stat().st_size
            if file_size <= 0:
                errors.append("OCR image must not be empty.")
            elif image_path.read_bytes()[:8] != _PNG_SIGNATURE:
                errors.append("OCR image is not a valid PNG.")

        return OCRValidationResult(
            valid=not errors,
            errors=tuple(errors),
            image_format=image_format,
            file_size=file_size,
        )
