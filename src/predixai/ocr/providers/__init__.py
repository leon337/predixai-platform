"""OCR provider adapters."""

from predixai.ocr.providers.base_provider import (
    BaseOCRProvider,
    OCRProviderExecution,
    OCRProviderStatus,
)
from predixai.ocr.providers.mock_provider import MockOCRProvider
from predixai.ocr.providers.provider_registry import ProviderRegistry
from predixai.ocr.providers.provider_selector import ProviderSelector
from predixai.ocr.providers.tesseract_provider import TesseractOCRProvider

__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "OCRProviderExecution",
    "OCRProviderStatus",
    "ProviderRegistry",
    "ProviderSelector",
    "TesseractOCRProvider",
]
