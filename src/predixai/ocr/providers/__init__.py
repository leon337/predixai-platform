"""OCR provider adapters."""

from predixai.ocr.providers.base_provider import BaseOCRProvider, OCRProviderStatus
from predixai.ocr.providers.mock_provider import MockOCRProvider
from predixai.ocr.providers.provider_registry import ProviderRegistry
from predixai.ocr.providers.provider_selector import ProviderSelector

__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "OCRProviderStatus",
    "ProviderRegistry",
    "ProviderSelector",
]
