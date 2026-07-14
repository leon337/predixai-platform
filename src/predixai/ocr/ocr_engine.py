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
from predixai.ocr.providers import MockOCRProvider, ProviderRegistry, ProviderSelector, TesseractOCRProvider
from predixai.ocr.providers.base_provider import OCRProviderExecution

_CACHE_SCHEMA_VERSION = "PTP-GOV.4.6C.1B.2"


class OCREngine:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.validator = OCRValidator()
        self.benchmark = OCRBenchmark(enabled=bool(self.config.get("benchmark_enabled", False)))
        self.cache_enabled = bool(self.config.get("cache_enabled", False))
        self.cache = OCRCache(Path(str(self.config.get("cache_directory", "data/ocr_cache"))))
        self.result_validator = OCRResultValidator(min_confidence=float(self.config.get("min_confidence", 0.0)))
        self.registry = ProviderRegistry()
        self.registry.register(MockOCRProvider())
        self.registry.register(TesseractOCRProvider(language=str(self.config.get("language", "por")), fallback_language=str(self.config.get("fallback_language", "eng")), psm=int(self.config.get("psm", 6)), timeout_seconds=int(self.config.get("timeout_seconds", 20))))
        self.selector = ProviderSelector(self.registry)

    def prepare_pipeline(self, image_path: str | Path) -> OCRResult:
        started_at = perf_counter()
        resolved_path = Path(image_path)
        validation = self.validator.validate(resolved_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        provider = self.selector.select(str(self.config.get("provider", "mock")))
        provider_status = provider.load()
        extraction_requested = bool(self.config.get("text_extraction_enabled", False))
        text_extraction_enabled = extraction_requested and provider_status.text_extraction_enabled and provider_status.ready
        privacy_sensitive = bool(self.config.get("privacy_sensitive", False))
        image_sha256 = self.cache.compute_image_sha256(resolved_path)
        namespace = {
            "schema_version": _CACHE_SCHEMA_VERSION,
            "provider": provider.name,
            "provider_version": provider_status.version,
            "configured_language": str(self.config.get("language", "")),
            "fallback_language": str(self.config.get("fallback_language", "")),
            "selected_language": provider_status.language,
            "psm": int(self.config.get("psm", 6)),
            "min_confidence": float(self.config.get("min_confidence", 0.0)),
            "text_extraction_enabled": text_extraction_enabled,
        }
        cache_key = self.cache.compute_key(resolved_path, namespace=namespace)
        effective_cache = self.cache_enabled and not privacy_sensitive and provider_status.ready and text_extraction_enabled
        if effective_cache:
            cached = self._load_cached_result(cache_key, resolved_path, validation.file_size, started_at)
            if cached is not None:
                return cached
        if not provider_status.ready:
            execution = OCRProviderExecution("OCR_ERROR", False, "", 0.0, "", "OCR provider is not ready.")
            benchmark_result = self.benchmark.disabled_result(execution, False)
        elif not text_extraction_enabled:
            execution = OCRProviderExecution("OCR_DISABLED", False, "", 0.0, provider_status.language, "")
            benchmark_result = self.benchmark.disabled_result(execution, False)
        else:
            execution, benchmark_result = self.benchmark.measure(lambda: provider.execute(resolved_path))
        checked = self.result_validator.validate(provider_status, execution, str(self.config.get("language", "")), str(self.config.get("fallback_language", "")))
        pipeline_ready = provider_status.ready and text_extraction_enabled and execution.status in {"OCR_COMPLETED", "OCR_EMPTY"}
        result = OCRResult(
            image_path=resolved_path,
            image_format=validation.image_format,
            file_size=validation.file_size,
            image_sha256=image_sha256,
            provider=provider.name,
            status=execution.status,
            pipeline_ready=pipeline_ready,
            text_extracted=execution.text_extracted and text_extraction_enabled,
            text=execution.text if text_extraction_enabled else "",
            confidence=execution.confidence if text_extraction_enabled else 0.0,
            language_used=execution.language_used,
            error=execution.error,
            validation_errors=checked.errors,
            validation_warnings=checked.warnings,
            min_confidence=checked.min_confidence,
            confidence_valid=checked.confidence_valid,
            language_valid=checked.language_valid,
            cache_hit=False,
            benchmark=benchmark_result.to_dict(),
            processing_time_ms=round((perf_counter() - started_at) * 1000, 3),
            timestamp=datetime.now().astimezone().isoformat(),
            provider_name=provider_status.name,
            selected_provider=provider.name,
            registered_providers=self.registry.provider_names,
            provider_loaded=provider_status.loaded,
            text_extraction_enabled=text_extraction_enabled,
            provider_ready=provider_status.ready,
            provider_version=provider_status.version,
            provider_language=provider_status.language,
            provider_installation_detected=provider_status.installation_detected,
            provider_language_available=provider_status.language_available,
        )
        if effective_cache and checked.valid and result.status == "OCR_COMPLETED" and result.pipeline_ready and result.text_extracted and not result.validation_errors and result.confidence_valid and result.language_valid:
            self.cache.save(cache_key, result.to_dict())
        return result

    def _load_cached_result(self, cache_key: str, image_path: Path, file_size: int, started_at: float) -> OCRResult | None:
        if not self.cache_enabled:
            return None
        cached_data = self.cache.load(cache_key)
        if cached_data is None:
            return None
        try:
            result = OCRResult.from_dict(cached_data)
        except (KeyError, TypeError, ValueError):
            return None
        if not (result.status == "OCR_COMPLETED" and result.pipeline_ready and result.text_extracted and not result.validation_errors and result.confidence_valid and result.language_valid):
            return None
        elapsed = round((perf_counter() - started_at) * 1000, 3)
        benchmark = self.benchmark.cache_hit_result(processing_time_ms=elapsed, text_length=len(result.text), status=result.status)
        return result.with_runtime_metadata(cache_hit=True, processing_time_ms=elapsed, timestamp=datetime.now().astimezone().isoformat(), benchmark=benchmark.to_dict(), image_path=image_path, file_size=file_size)
