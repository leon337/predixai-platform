"""OCR provider contract for the foundation phase."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OCRProviderStatus:
    """Loaded OCR provider metadata without a real OCR backend."""

    name: str
    loaded: bool
    text_extraction_enabled: bool


class OCRProvider:
    """Foundation OCR provider with no text extraction backend."""

    name = "PredixAI OCR Foundation Provider"

    def load(self) -> OCRProviderStatus:
        """Return provider status without loading external OCR libraries."""
        return OCRProviderStatus(
            name=self.name,
            loaded=True,
            text_extraction_enabled=False,
        )
