"""OCR Engine foundation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_validator import OCRValidator
from predixai.ocr.providers import MockOCRProvider, ProviderRegistry, ProviderSelector


class OCREngine:
    """Prepare the OCR pipeline without extracting text."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.validator = OCRValidator()
        self.registry = ProviderRegistry()
        self.registry.register(MockOCRProvider())
        self.selector = ProviderSelector(self.registry)

    def prepare_pipeline(self, image_path: str | Path) -> OCRResult:
        """Validate the ROI image and prepare the OCR pipeline contract."""
        started_at = perf_counter()
        resolved_path = Path(image_path)
        validation = self.validator.validate(resolved_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        provider_name = str(self.config.get("provider", "mock"))
        provider = self.selector.select(provider_name)
        provider_status = provider.load()
        text_extraction_enabled = (
            bool(self.config.get("text_extraction_enabled", False))
            and provider_status.text_extraction_enabled
        )
        execution = provider.execute(resolved_path)
        processing_time_ms = round((perf_counter() - started_at) * 1000, 3)
        timestamp = datetime.now().astimezone().isoformat()

        return OCRResult(
            image_path=resolved_path,
            image_format=validation.image_format,
            file_size=validation.file_size,
            provider=provider.name,
            status=execution.status,
            pipeline_ready=True,
            text_extracted=execution.text_extracted and text_extraction_enabled,
            text=execution.text if text_extraction_enabled else "",
            confidence=execution.confidence if text_extraction_enabled else 0.0,
            processing_time_ms=processing_time_ms,
            timestamp=timestamp,
            provider_name=provider_status.name,
            selected_provider=provider.name,
            registered_providers=self.registry.provider_names,
            provider_loaded=provider_status.loaded,
            text_extraction_enabled=text_extraction_enabled,
        )
