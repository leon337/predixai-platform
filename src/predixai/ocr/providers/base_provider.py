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


@dataclass(frozen=True)
class OCRProviderExecution:
    """OCR provider execution metadata without extracted text."""

    status: str
    text_extracted: bool
    text: str
    confidence: float


class BaseOCRProvider(ABC):
    """Contract for future OCR providers."""

    name: str

    @abstractmethod
    def load(self) -> OCRProviderStatus:
        """Load provider metadata without extracting text."""

    @abstractmethod
    def execute(self, image_path: object) -> OCRProviderExecution:
        """Execute provider pipeline without extracting text."""
