"""OCR result validation."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.ocr.providers.base_provider import (
    OCRProviderExecution,
    OCRProviderStatus,
)


@dataclass(frozen=True)
class OCRResultValidation:
    """Validation metadata for an OCR execution."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    min_confidence: float
    confidence_valid: bool
    language_valid: bool


class OCRResultValidator:
    """Validate OCR provider execution metadata."""

    def __init__(self, min_confidence: float = 0.0) -> None:
        self.min_confidence = min_confidence

    def validate(
        self,
        provider_status: OCRProviderStatus,
        execution: OCRProviderExecution,
        configured_language: str,
        fallback_language: str,
    ) -> OCRResultValidation:
        """Validate language, confidence and provider execution status."""
        errors: list[str] = []
        warnings: list[str] = []

        if not provider_status.installation_detected:
            errors.append("Tesseract installation was not detected.")

        if not provider_status.ready:
            errors.append("OCR provider is not ready.")

        if execution.status in {"OCR_ERROR", "OCR_TIMEOUT"}:
            errors.append(execution.error or "OCR provider execution failed.")

        language_valid = self._validate_language(
            provider_status=provider_status,
            execution=execution,
            configured_language=configured_language,
            fallback_language=fallback_language,
            warnings=warnings,
        )

        confidence_valid = self._validate_confidence(execution, warnings)

        return OCRResultValidation(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
            min_confidence=self.min_confidence,
            confidence_valid=confidence_valid,
            language_valid=language_valid,
        )

    def _validate_language(
        self,
        provider_status: OCRProviderStatus,
        execution: OCRProviderExecution,
        configured_language: str,
        fallback_language: str,
        warnings: list[str],
    ) -> bool:
        if execution.language_used == configured_language:
            return True

        if (
            not provider_status.language_available
            and fallback_language
            and execution.language_used == fallback_language
        ):
            warnings.append(
                "Configured OCR language is unavailable; fallback was used."
            )
            return True

        warnings.append("OCR language differs from the configured language.")
        return False

    def _validate_confidence(
        self,
        execution: OCRProviderExecution,
        warnings: list[str],
    ) -> bool:
        if not execution.text_extracted:
            return True

        if execution.confidence >= self.min_confidence:
            return True

        warnings.append("OCR confidence is below the configured minimum.")
        return False
