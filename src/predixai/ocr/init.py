"""OCR foundation entrypoint."""

from predixai.ocr.ocr_engine import OCREngine
from predixai.ocr.ocr_cache import OCRCache
from predixai.ocr.ocr_provider import OCRProvider, OCRProviderStatus
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_result_validator import (
    OCRResultValidation,
    OCRResultValidator,
)
from predixai.ocr.ocr_validator import OCRValidationResult, OCRValidator
from predixai.ocr.providers import (
    BaseOCRProvider,
    MockOCRProvider,
    OCRProviderExecution,
    ProviderRegistry,
    ProviderSelector,
)

__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "OCRCache",
    "OCREngine",
    "OCRProviderExecution",
    "OCRProvider",
    "OCRProviderStatus",
    "OCRResult",
    "OCRResultValidation",
    "OCRResultValidator",
    "OCRValidationResult",
    "OCRValidator",
    "ProviderRegistry",
    "ProviderSelector",
]
