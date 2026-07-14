"""Tesseract OCR provider."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from csv import DictReader
from io import StringIO
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
_LANGUAGE_TOKEN = re.compile(r"^[A-Za-z0-9_+.-]+$")


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract provider adapter with fail-closed parameter validation."""

    name = "tesseract"

    def __init__(
        self,
        language: str = "por",
        fallback_language: str = "eng",
        psm: int = 6,
        timeout_seconds: int | float = 20,
    ) -> None:
        normalized_language = language.strip()
        normalized_fallback = fallback_language.strip()
        if not normalized_language or _LANGUAGE_TOKEN.fullmatch(normalized_language) is None:
            raise ValueError("configured Tesseract language is invalid")
        if normalized_fallback and _LANGUAGE_TOKEN.fullmatch(normalized_fallback) is None:
            raise ValueError("fallback Tesseract language is invalid")
        if isinstance(psm, bool) or not isinstance(psm, int) or not 0 <= psm <= 13:
            raise ValueError("Tesseract PSM must be an integer between 0 and 13")
        timeout = float(timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Tesseract timeout must be finite and greater than zero")

        self.language = normalized_language
        self.fallback_language = normalized_fallback
        self.psm = psm
        self.timeout_seconds = timeout
        self.binary_path = self._resolve_binary_path()
        self._selected_language = ""

    def load(self) -> OCRProviderStatus:
        """Validate Tesseract availability without extracting text."""
        installation_detected = self.binary_path is not None
        version = self._detect_version()
        languages = self._detect_languages()
        selected = self._select_language(languages)
        self._selected_language = selected
        ready = installation_detected and bool(selected)
        return OCRProviderStatus(
            name=self.name,
            loaded=installation_detected,
            text_extraction_enabled=ready,
            ready=ready,
            version=version,
            language=selected,
            installation_detected=installation_detected,
            language_available=bool(selected),
        )

    def execute(self, image_path: object) -> OCRProviderExecution:
        """Execute Tesseract against one validated PNG."""
        if self.binary_path is None:
            return OCRProviderExecution(
                "OCR_ERROR",
                False,
                "",
                0.0,
                "",
                "Tesseract executable was not detected.",
            )

        language_used = self._selected_language or self._select_language()
        if not language_used:
            return OCRProviderExecution(
                "OCR_ERROR",
                False,
                "",
                0.0,
                "",
                "No Tesseract language is available.",
            )

        command = [
            self.binary_path,
            str(Path(str(image_path))),
            "stdout",
            "-l",
            language_used,
            "--psm",
            str(self.psm),
            "tsv",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return OCRProviderExecution(
                "OCR_TIMEOUT",
                False,
                "",
                0.0,
                language_used,
                "Tesseract OCR timed out.",
            )
        except OSError as exc:
            return OCRProviderExecution(
                "OCR_ERROR",
                False,
                "",
                0.0,
                language_used,
                f"Tesseract execution failed: {type(exc).__name__}.",
            )

        if completed.returncode != 0:
            return OCRProviderExecution(
                "OCR_ERROR",
                False,
                "",
                0.0,
                language_used,
                (completed.stderr or "").strip() or "Tesseract OCR failed.",
            )

        text, confidence = self._parse_tsv_output(completed.stdout or "")
        return OCRProviderExecution(
            "OCR_COMPLETED" if text else "OCR_EMPTY",
            bool(text),
            text,
            confidence,
            language_used,
            "",
        )

    def _resolve_binary_path(self) -> str | None:
        detected = shutil.which("tesseract")
        if detected:
            return str(Path(detected).resolve())
        for candidate in _COMMON_TESSERACT_PATHS:
            if candidate.exists():
                return str(candidate.resolve())
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
        if completed.returncode != 0:
            return "not_detected"
        output = (completed.stdout or "").strip()
        return output.splitlines()[0].strip() if output else "unknown"

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
        if completed.returncode != 0:
            return ()
        return tuple(
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
            and not line.lower().startswith("list of")
            and _LANGUAGE_TOKEN.fullmatch(line.strip())
        )

    def _select_language(
        self,
        available_languages: tuple[str, ...] | None = None,
    ) -> str:
        languages = (
            available_languages
            if available_languages is not None
            else self._detect_languages()
        )
        if self.language in languages:
            return self.language
        if self.fallback_language and self.fallback_language in languages:
            return self.fallback_language
        return ""

    def _parse_tsv_output(self, output: str) -> tuple[str, float]:
        words: list[str] = []
        confidences: list[float] = []
        for row in DictReader(StringIO(output), delimiter="\t"):
            text = (row.get("text") or "").strip()
            if not text:
                continue
            try:
                confidence = float((row.get("conf") or "").strip())
            except ValueError:
                continue
            if not math.isfinite(confidence) or confidence < 0:
                continue
            words.append(text)
            confidences.append(confidence)
        average = (
            round(sum(confidences) / len(confidences), 3)
            if confidences
            else 0.0
        )
        return " ".join(words), average
