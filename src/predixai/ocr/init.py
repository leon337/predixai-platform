"""OCR foundation entrypoint."""

from predixai.ocr.ocr_engine import OCREngine
from predixai.ocr.ocr_provider import OCRProvider, OCRProviderStatus
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_validator import OCRValidationResult, OCRValidator

__all__ = [
    "OCREngine",
    "OCRProvider",
    "OCRProviderStatus",
    "OCRResult",
    "OCRValidationResult",
    "OCRValidator",
]
