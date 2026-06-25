"""OCR Engine foundation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from predixai.ocr.ocr_provider import OCRProvider
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_validator import OCRValidator


class OCREngine:
    """Prepare the OCR pipeline without extracting text."""

    def __init__(self) -> None:
        self.provider = OCRProvider()
        self.validator = OCRValidator()

    def prepare_pipeline(self, image_path: str | Path) -> OCRResult:
        """Validate the ROI image and prepare the OCR pipeline contract."""
        resolved_path = Path(image_path)
        validation = self.validator.validate(resolved_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        provider_status = self.provider.load()
        return OCRResult(
            image_path=resolved_path,
            image_format=validation.image_format,
            file_size=validation.file_size,
            provider_name=provider_status.name,
            provider_loaded=provider_status.loaded,
            pipeline_ready=True,
            text_extraction_enabled=provider_status.text_extraction_enabled,
            created_at=datetime.now().astimezone().isoformat(),
        )
