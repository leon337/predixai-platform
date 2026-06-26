"""Tesseract OCR provider."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from predixai.ocr.providers.base_provider import (
    BaseOCRProvider,
    OCRProviderExecution,
    OCRProviderStatus,
)

_COMMON_TESSERACT_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract provider adapter."""

    name = "tesseract"

    def __init__(
        self,
        language: str = "por",
        fallback_language: str = "eng",
        psm: int = 6,
        timeout_seconds: int = 20,
    ) -> None:
        self.language = language
        self.fallback_language = fallback_language
        self.psm = psm
        self.timeout_seconds = timeout_seconds
        self.binary_path = self._resolve_binary_path()

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
            text_extraction_enabled=True,
            ready=True,
            version=version,
            language=self.language,
            installation_detected=self.binary_path is not None,
            language_available=language_available,
        )

    def execute(self, image_path: object) -> OCRProviderExecution:
        """Execute Tesseract OCR against an image path."""
        if self.binary_path is None:
            return OCRProviderExecution(
                status="OCR_ERROR",
                text_extracted=False,
                text="",
                confidence=0.0,
                language_used="",
                error="Tesseract executable was not detected.",
            )

        language_used = self._select_language()
        if not language_used:
            return OCRProviderExecution(
                status="OCR_ERROR",
                text_extracted=False,
                text="",
                confidence=0.0,
                language_used="",
                error="No Tesseract language is available.",
            )

        image = Path(str(image_path))
        command = [
            self.binary_path,
            str(image),
            "stdout",
            "-l",
            language_used,
            "--psm",
            str(self.psm),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return OCRProviderExecution(
                status="OCR_TIMEOUT",
                text_extracted=False,
                text="",
                confidence=0.0,
                language_used=language_used,
                error="Tesseract OCR timed out.",
            )

        text = (completed.stdout or "").strip()
        error_output = (completed.stderr or "").strip()
        if completed.returncode != 0:
            return OCRProviderExecution(
                status="OCR_ERROR",
                text_extracted=False,
                text="",
                confidence=0.0,
                language_used=language_used,
                error=error_output or "Tesseract OCR failed.",
            )

        return OCRProviderExecution(
            status="OCR_COMPLETED" if text else "OCR_EMPTY",
            text_extracted=bool(text),
            text=text,
            confidence=0.0,
            language_used=language_used,
            error="",
        )

    def _resolve_binary_path(self) -> str | None:
        detected = shutil.which("tesseract")
        if detected:
            return detected

        for candidate in _COMMON_TESSERACT_PATHS:
            if candidate.exists():
                return str(candidate)

        return None

    def _detect_version(self) -> str:
        if self.binary_path is None:
            return "not_detected"

        try:
            completed = subprocess.run(
                [self.binary_path, "--version"],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "not_detected"
        output = (completed.stdout or completed.stderr).strip()
        if not output:
            return "unknown"
        return output.splitlines()[0].strip()

    def _detect_languages(self) -> tuple[str, ...]:
        if self.binary_path is None:
            return ()

        try:
            completed = subprocess.run(
                [self.binary_path, "--list-langs"],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ()
        output = (completed.stdout or completed.stderr).splitlines()
        return tuple(
            line.strip()
            for line in output
            if line.strip() and not line.lower().startswith("list of")
        )

    def _select_language(self) -> str:
        available_languages = self._detect_languages()
        if self.language in available_languages:
            return self.language

        if self.fallback_language in available_languages:
            return self.fallback_language

        return self.language if self.language else ""
