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
    ready: bool = False
    version: str = ""
    language: str = ""
    installation_detected: bool = False
    language_available: bool = False


@dataclass(frozen=True)
class OCRProviderExecution:
    """OCR provider execution metadata."""

    status: str
    text_extracted: bool
    text: str
    confidence: float
    language_used: str = ""
    error: str = ""


class BaseOCRProvider(ABC):
    """Contract for future OCR providers."""

    name: str

    @abstractmethod
    def load(self) -> OCRProviderStatus:
        """Load provider metadata without extracting text."""

    @abstractmethod
    def execute(self, image_path: object) -> OCRProviderExecution:
        """Execute provider pipeline."""
