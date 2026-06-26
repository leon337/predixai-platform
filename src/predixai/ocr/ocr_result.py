"""OCR result metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRResult:
    """Technical OCR pipeline result."""

    image_path: Path
    image_format: str
    file_size: int
    provider: str
    status: str
    pipeline_ready: bool
    text_extracted: bool
    text: str
    confidence: float
    language_used: str
    error: str
    validation_errors: tuple[str, ...]
    validation_warnings: tuple[str, ...]
    min_confidence: float
    confidence_valid: bool
    language_valid: bool
    processing_time_ms: float
    timestamp: str
    provider_name: str
    selected_provider: str
    registered_providers: tuple[str, ...]
    provider_loaded: bool
    text_extraction_enabled: bool
    provider_ready: bool
    provider_version: str
    provider_language: str
    provider_installation_detected: bool
    provider_language_available: bool

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "image_path": str(self.image_path),
            "image_format": self.image_format,
            "file_size": self.file_size,
            "provider": self.provider,
            "status": self.status,
            "pipeline_ready": self.pipeline_ready,
            "text_extracted": self.text_extracted,
            "text": self.text,
            "confidence": self.confidence,
            "language_used": self.language_used,
            "error": self.error,
            "validation_errors": list(self.validation_errors),
            "validation_warnings": list(self.validation_warnings),
            "min_confidence": self.min_confidence,
            "confidence_valid": self.confidence_valid,
            "language_valid": self.language_valid,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp,
            "provider_name": self.provider_name,
            "selected_provider": self.selected_provider,
            "registered_providers": list(self.registered_providers),
            "provider_loaded": self.provider_loaded,
            "text_extraction_enabled": self.text_extraction_enabled,
            "provider_ready": self.provider_ready,
            "provider_version": self.provider_version,
            "provider_language": self.provider_language,
            "provider_installation_detected": (
                self.provider_installation_detected
            ),
            "provider_language_available": self.provider_language_available,
        }
