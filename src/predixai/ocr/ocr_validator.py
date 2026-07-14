"""OCR image validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_OCR_INPUT_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class OCRValidationResult:
    valid: bool
    errors: tuple[str, ...]
    image_format: str
    file_size: int


class OCRValidator:
    """Validate that an OCR input is a safe, decodable PNG."""

    def validate(self, image_path: Path) -> OCRValidationResult:
        errors: list[str] = []
        image_format = image_path.suffix.lstrip(".").lower()
        file_size = 0

        try:
            if image_path.is_symlink():
                errors.append("OCR image path must not be a symbolic link.")
            elif not image_path.exists():
                errors.append(f"OCR image does not exist: {image_path}")
            elif not image_path.is_file():
                errors.append(f"OCR image path is not a file: {image_path}")
        except OSError:
            errors.append("OCR image metadata could not be read.")

        if image_format != "png":
            errors.append("OCR image extension must be PNG.")

        if not errors:
            try:
                file_size = image_path.stat().st_size
                if file_size <= 0:
                    errors.append("OCR image must not be empty.")
                elif file_size > _MAX_OCR_INPUT_BYTES:
                    errors.append("OCR image exceeds the maximum allowed size.")
                else:
                    with image_path.open("rb") as handle:
                        signature = handle.read(8)
                    if signature != _PNG_SIGNATURE:
                        errors.append("OCR image is not a valid PNG.")
                    else:
                        with Image.open(image_path) as image:
                            width, height = image.size
                            image.verify()
                        if width <= 0 or height <= 0:
                            errors.append(
                                "OCR image dimensions must be positive."
                            )
            except (
                OSError,
                UnidentifiedImageError,
                SyntaxError,
                ValueError,
            ):
                errors.append("OCR image could not be decoded as PNG.")

        return OCRValidationResult(
            valid=not errors,
            errors=tuple(dict.fromkeys(errors)),
            image_format=image_format,
            file_size=file_size,
        )
