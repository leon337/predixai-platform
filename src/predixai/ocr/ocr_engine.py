"""OCR Engine."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from predixai.ocr.ocr_benchmark import OCRBenchmark
from predixai.ocr.ocr_cache import OCRCache
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_result_validator import OCRResultValidator
from predixai.ocr.ocr_validator import OCRValidator
from predixai.ocr.providers import (
    MockOCRProvider,
    ProviderRegistry,
    ProviderSelector,
    TesseractOCRProvider,
)


class OCREngine:
    """Execute the OCR pipeline."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.validator = OCRValidator()
        self.benchmark = OCRBenchmark(
            enabled=bool(self.config.get("benchmark_enabled", False))
        )
        self.cache_enabled = bool(self.config.get("cache_enabled", False))
        self.cache = OCRCache(
            Path(str(self.config.get("cache_directory", "data/ocr_cache")))
        )
        self.result_validator = OCRResultValidator(
            min_confidence=float(self.config.get("min_confidence", 0.0))
        )
        self.registry = ProviderRegistry()
        self.registry.register(MockOCRProvider())
        self.registry.register(
            TesseractOCRProvider(
                language=str(self.config.get("language", "por")),
                fallback_language=str(
                    self.config.get("fallback_language", "eng")
                ),
                psm=int(self.config.get("psm", 6)),
                timeout_seconds=int(self.config.get("timeout_seconds", 20)),
            )
        )
        self.selector = ProviderSelector(self.registry)

    def prepare_pipeline(self, image_path: str | Path) -> OCRResult:
        """Validate the ROI image and execute the selected OCR provider."""
        started_at = perf_counter()
        resolved_path = Path(image_path)
        validation = self.validator.validate(resolved_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        image_sha256 = self.cache.compute_key(resolved_path)
        cached_result = self._load_cached_result(image_sha256, started_at)
        if cached_result is not None:
            return cached_result

        provider_name = str(self.config.get("provider", "mock"))
        provider = self.selector.select(provider_name)
        provider_status = provider.load()
        text_extraction_enabled = (
            bool(self.config.get("text_extraction_enabled", False))
            and provider_status.text_extraction_enabled
        )
        execution, benchmark_result = self.benchmark.measure(
            lambda: provider.execute(resolved_path)
        )
        result_validation = self.result_validator.validate(
            provider_status=provider_status,
            execution=execution,
            configured_language=str(self.config.get("language", "")),
            fallback_language=str(self.config.get("fallback_language", "")),
        )
        processing_time_ms = round((perf_counter() - started_at) * 1000, 3)
        timestamp = datetime.now().astimezone().isoformat()

        result = OCRResult(
            image_path=resolved_path,
            image_format=validation.image_format,
            file_size=validation.file_size,
            image_sha256=image_sha256,
            provider=provider.name,
            status=execution.status,
            pipeline_ready=True,
            text_extracted=execution.text_extracted and text_extraction_enabled,
            text=execution.text if text_extraction_enabled else "",
            confidence=execution.confidence if text_extraction_enabled else 0.0,
            language_used=execution.language_used,
            error=execution.error,
            validation_errors=result_validation.errors,
            validation_warnings=result_validation.warnings,
            min_confidence=result_validation.min_confidence,
            confidence_valid=result_validation.confidence_valid,
            language_valid=result_validation.language_valid,
            cache_hit=False,
            benchmark=benchmark_result.to_dict(),
            processing_time_ms=processing_time_ms,
            timestamp=timestamp,
            provider_name=provider_status.name,
            selected_provider=provider.name,
            registered_providers=self.registry.provider_names,
            provider_loaded=provider_status.loaded,
            text_extraction_enabled=text_extraction_enabled,
            provider_ready=provider_status.ready,
            provider_version=provider_status.version,
            provider_language=provider_status.language,
            provider_installation_detected=(
                provider_status.installation_detected
            ),
            provider_language_available=provider_status.language_available,
        )
        if self.cache_enabled:
            self.cache.save(image_sha256, result.to_dict())

        return result

    def _load_cached_result(
        self,
        image_sha256: str,
        started_at: float,
    ) -> OCRResult | None:
        if not self.cache_enabled:
            return None

        cached_data = self.cache.load(image_sha256)
        if cached_data is None:
            return None

        try:
            result = OCRResult.from_dict(cached_data)
        except (KeyError, TypeError, ValueError):
            return None

        processing_time_ms = round((perf_counter() - started_at) * 1000, 3)
        timestamp = datetime.now().astimezone().isoformat()
        benchmark_result = self.benchmark.cache_hit_result(
            processing_time_ms=processing_time_ms,
            text_length=len(result.text),
            status=result.status,
        )
        return result.with_runtime_metadata(
            cache_hit=True,
            processing_time_ms=processing_time_ms,
            timestamp=timestamp,
            benchmark=benchmark_result.to_dict(),
        )
