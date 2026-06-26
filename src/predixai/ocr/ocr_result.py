"""OCR result metadata."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class OCRResult:
    """Technical OCR pipeline result."""

    image_path: Path
    image_format: str
    file_size: int
    image_sha256: str
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
    cache_hit: bool
    benchmark: dict[str, object]
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

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OCRResult":
        """Create an OCRResult from cached serializable data."""
        return cls(
            image_path=Path(str(data["image_path"])),
            image_format=str(data["image_format"]),
            file_size=int(data["file_size"]),
            image_sha256=str(data["image_sha256"]),
            provider=str(data["provider"]),
            status=str(data["status"]),
            pipeline_ready=bool(data["pipeline_ready"]),
            text_extracted=bool(data["text_extracted"]),
            text=str(data["text"]),
            confidence=float(data["confidence"]),
            language_used=str(data["language_used"]),
            error=str(data["error"]),
            validation_errors=tuple(
                str(item) for item in data.get("validation_errors", [])
            ),
            validation_warnings=tuple(
                str(item) for item in data.get("validation_warnings", [])
            ),
            min_confidence=float(data["min_confidence"]),
            confidence_valid=bool(data["confidence_valid"]),
            language_valid=bool(data["language_valid"]),
            cache_hit=bool(data.get("cache_hit", False)),
            benchmark=dict(data.get("benchmark", {})),
            processing_time_ms=float(data["processing_time_ms"]),
            timestamp=str(data["timestamp"]),
            provider_name=str(data["provider_name"]),
            selected_provider=str(data["selected_provider"]),
            registered_providers=tuple(
                str(item) for item in data.get("registered_providers", [])
            ),
            provider_loaded=bool(data["provider_loaded"]),
            text_extraction_enabled=bool(data["text_extraction_enabled"]),
            provider_ready=bool(data["provider_ready"]),
            provider_version=str(data["provider_version"]),
            provider_language=str(data["provider_language"]),
            provider_installation_detected=bool(
                data["provider_installation_detected"]
            ),
            provider_language_available=bool(
                data["provider_language_available"]
            ),
        )

    def with_runtime_metadata(
        self,
        *,
        cache_hit: bool,
        processing_time_ms: float,
        timestamp: str,
        benchmark: dict[str, object] | None = None,
        image_path: Path | None = None,
        file_size: int | None = None,
    ) -> "OCRResult":
        """Return this OCRResult with runtime-only metadata updated."""
        return replace(
            self,
            image_path=image_path if image_path is not None else self.image_path,
            file_size=file_size if file_size is not None else self.file_size,
            cache_hit=cache_hit,
            processing_time_ms=processing_time_ms,
            timestamp=timestamp,
            benchmark=benchmark if benchmark is not None else self.benchmark,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "image_path": str(self.image_path),
            "image_format": self.image_format,
            "file_size": self.file_size,
            "image_sha256": self.image_sha256,
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
            "cache_hit": self.cache_hit,
            "benchmark": self.benchmark,
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
