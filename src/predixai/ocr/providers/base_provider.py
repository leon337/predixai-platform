"""Base OCR provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRProviderStatus:
    """Loaded OCR provider metadata without text extraction."""

    name: str
    loaded: bool
    text_extraction_enabled: bool


class BaseOCRProvider(ABC):
    """Contract for future OCR providers."""

    name: str

    @abstractmethod
    def load(self) -> OCRProviderStatus:
        """Load provider metadata without extracting text."""
