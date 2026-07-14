"""OCR benchmark utilities."""

from __future__ import annotations

import tracemalloc
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, TypeVar

from predixai.ocr.providers.base_provider import OCRProviderExecution

T = TypeVar("T", bound=OCRProviderExecution)


@dataclass(frozen=True)
class OCRBenchmarkResult:
    enabled: bool
    cache_hit: bool
    provider_processing_time_ms: float
    peak_memory_kb: float
    current_memory_kb: float
    text_length: int
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "cache_hit": self.cache_hit,
            "provider_processing_time_ms": self.provider_processing_time_ms,
            "peak_memory_kb": self.peak_memory_kb,
            "current_memory_kb": self.current_memory_kb,
            "text_length": self.text_length,
            "status": self.status,
        }


class OCRBenchmark:
    """Measure OCR provider performance without leaking tracemalloc state."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def measure(
        self,
        operation: Callable[[], T],
        *,
        cache_hit: bool = False,
    ) -> tuple[T, OCRBenchmarkResult]:
        if not self.enabled:
            execution = operation()
            return execution, self.disabled_result(execution, cache_hit)

        tracemalloc.start()
        started_at = perf_counter()
        try:
            execution = operation()
            processing_time = round(
                (perf_counter() - started_at) * 1000,
                3,
            )
            current_memory, peak_memory = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        return execution, OCRBenchmarkResult(
            enabled=True,
            cache_hit=cache_hit,
            provider_processing_time_ms=processing_time,
            peak_memory_kb=round(peak_memory / 1024, 3),
            current_memory_kb=round(current_memory / 1024, 3),
            text_length=len(execution.text),
            status=execution.status,
        )

    def cache_hit_result(
        self,
        *,
        processing_time_ms: float,
        text_length: int,
        status: str,
    ) -> OCRBenchmarkResult:
        return OCRBenchmarkResult(
            enabled=self.enabled,
            cache_hit=True,
            provider_processing_time_ms=processing_time_ms,
            peak_memory_kb=0.0,
            current_memory_kb=0.0,
            text_length=text_length,
            status=status,
        )

    def disabled_result(
        self,
        execution: OCRProviderExecution,
        cache_hit: bool,
    ) -> OCRBenchmarkResult:
        return OCRBenchmarkResult(
            enabled=False,
            cache_hit=cache_hit,
            provider_processing_time_ms=0.0,
            peak_memory_kb=0.0,
            current_memory_kb=0.0,
            text_length=len(execution.text),
            status=execution.status,
        )
