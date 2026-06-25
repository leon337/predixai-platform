"""Compatibility OCR provider entrypoint."""

from __future__ import annotations

from predixai.ocr.providers.base_provider import OCRProviderStatus
from predixai.ocr.providers.mock_provider import MockOCRProvider


class OCRProvider(MockOCRProvider):
    """Default OCR provider alias for the foundation phase."""
