"""Tesseract OCR provider foundation."""

from __future__ import annotations

import shutil
import subprocess

from predixai.ocr.providers.base_provider import (
    BaseOCRProvider,
    OCRProviderExecution,
    OCRProviderStatus,
)


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract provider adapter without real text extraction."""

    name = "tesseract"

    def __init__(self, language: str = "por") -> None:
        self.language = language
        self.binary_path = shutil.which("tesseract")

    def load(self) -> OCRProviderStatus:
        """Validate Tesseract availability without extracting text."""
        version = self._detect_version()
        available_languages = self._detect_languages()
        language_available = (
            self.language in available_languages
            if available_languages
            else False
        )

        return OCRProviderStatus(
            name=self.name,
            loaded=True,
            text_extraction_enabled=False,
            ready=True,
            version=version,
            language=self.language,
            installation_detected=self.binary_path is not None,
            language_available=language_available,
        )

    def execute(self, image_path: object) -> OCRProviderExecution:
        """Prepare Tesseract pipeline without invoking OCR."""
        return OCRProviderExecution(
            status="READY",
            text_extracted=False,
            text="",
            confidence=0.0,
        )

    def _detect_version(self) -> str:
        if self.binary_path is None:
            return "not_detected"

        completed = subprocess.run(
            [self.binary_path, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        output = (completed.stdout or completed.stderr).strip()
        if not output:
            return "unknown"
        return output.splitlines()[0].strip()

    def _detect_languages(self) -> tuple[str, ...]:
        if self.binary_path is None:
            return ()

        completed = subprocess.run(
            [self.binary_path, "--list-langs"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        output = (completed.stdout or completed.stderr).splitlines()
        return tuple(
            line.strip()
            for line in output
            if line.strip() and not line.lower().startswith("list of")
        )
