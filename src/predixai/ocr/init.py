"""OCR foundation entrypoint."""

from predixai.ocr.ocr_engine import OCREngine
from predixai.ocr.ocr_provider import OCRProvider, OCRProviderStatus
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_validator import OCRValidationResult, OCRValidator
from predixai.ocr.providers import (
    BaseOCRProvider,
    MockOCRProvider,
    ProviderRegistry,
    ProviderSelector,
)

__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "OCREngine",
    "OCRProvider",
    "OCRProviderStatus",
    "OCRResult",
    "OCRValidationResult",
    "OCRValidator",
    "ProviderRegistry",
    "ProviderSelector",
]
