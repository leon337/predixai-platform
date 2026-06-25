"""Mock OCR provider for the foundation phase."""

from __future__ import annotations

from predixai.ocr.providers.base_provider import BaseOCRProvider, OCRProviderStatus


class MockOCRProvider(BaseOCRProvider):
    """Mock provider that never extracts text."""

    name = "mock"

    def load(self) -> OCRProviderStatus:
        """Return mock provider status without loading OCR libraries."""
        return OCRProviderStatus(
            name=self.name,
            loaded=True,
            text_extraction_enabled=False,
        )
