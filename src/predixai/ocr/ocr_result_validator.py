"""OCR result validation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from predixai.ocr.providers.base_provider import (
    OCRProviderExecution,
    OCRProviderStatus,
)


@dataclass(frozen=True)
class OCRResultValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    min_confidence: float
    confidence_valid: bool
    language_valid: bool


class OCRResultValidator:
    """Validate OCR execution with strict provider/language binding."""

    def __init__(self, min_confidence: float = 0.0) -> None:
        threshold = float(min_confidence)
        if not math.isfinite(threshold) or not 0.0 <= threshold <= 100.0:
            raise ValueError("OCR minimum confidence must be between 0 and 100")
        self.min_confidence = threshold

    def validate(
        self,
        provider_status: OCRProviderStatus,
        execution: OCRProviderExecution,
        configured_language: str,
        fallback_language: str,
    ) -> OCRResultValidation:
        errors: list[str] = []
        warnings: list[str] = []
        strict = provider_status.name == "tesseract"

        if not provider_status.installation_detected:
            errors.append("Tesseract installation was not detected.")
        if not provider_status.ready:
            errors.append("OCR provider is not ready.")
        if execution.status in {"OCR_ERROR", "OCR_TIMEOUT"}:
            errors.append(execution.error or "OCR provider execution failed.")

        allowed_languages = {
            value
            for value in (configured_language.strip(), fallback_language.strip())
            if value
        }
        if strict:
            language_valid = (
                bool(provider_status.language)
                and execution.language_used == provider_status.language
                and provider_status.language in allowed_languages
            )
            if execution.language_used != provider_status.language:
                errors.append("LANGUAGE_PROVIDER_EXECUTION_MISMATCH")
            elif provider_status.language not in allowed_languages:
                errors.append("LANGUAGE_NOT_CONFIGURED_OR_FALLBACK")
            elif provider_status.language != configured_language:
                warnings.append(
                    "Configured OCR language is unavailable; fallback was used."
                )
        else:
            language_valid = (
                not execution.language_used
                or execution.language_used in allowed_languages
            )

        if not execution.text_extracted:
            confidence_valid = not strict
            if strict:
                warnings.append("OCR did not extract text.")
        else:
            confidence_valid = (
                math.isfinite(execution.confidence)
                and execution.confidence >= self.min_confidence
            )
            if not confidence_valid:
                warnings.append(
                    "OCR confidence is below the configured minimum."
                )

        if strict and execution.status != "OCR_COMPLETED":
            warnings.append(
                "Tesseract execution did not complete with text."
            )

        valid = not errors
        if strict:
            valid = (
                valid
                and execution.status == "OCR_COMPLETED"
                and execution.text_extracted
                and language_valid
                and confidence_valid
            )

        return OCRResultValidation(
            valid=valid,
            errors=tuple(dict.fromkeys(errors)),
            warnings=tuple(dict.fromkeys(warnings)),
            min_confidence=self.min_confidence,
            confidence_valid=confidence_valid,
            language_valid=language_valid,
        )
