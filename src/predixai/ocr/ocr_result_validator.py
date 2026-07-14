"""OCR result validation."""

from __future__ import annotations

from dataclasses import dataclass
from predixai.ocr.providers.base_provider import OCRProviderExecution, OCRProviderStatus


@dataclass(frozen=True)
class OCRResultValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    min_confidence: float
    confidence_valid: bool
    language_valid: bool


class OCRResultValidator:
    def __init__(self, min_confidence: float = 0.0) -> None:
        self.min_confidence = min_confidence

    def validate(self, provider_status: OCRProviderStatus, execution: OCRProviderExecution, configured_language: str, fallback_language: str) -> OCRResultValidation:
        errors: list[str] = []
        warnings: list[str] = []
        strict = provider_status.name == "tesseract"
        if not provider_status.installation_detected:
            errors.append("Tesseract installation was not detected.")
        if not provider_status.ready:
            errors.append("OCR provider is not ready.")
        if execution.status in {"OCR_ERROR", "OCR_TIMEOUT"}:
            errors.append(execution.error or "OCR provider execution failed.")
        language_valid = execution.language_used == configured_language
        if not language_valid and fallback_language and execution.language_used == fallback_language:
            warnings.append("Configured OCR language is unavailable; fallback was used.")
            language_valid = True
        elif not language_valid:
            warnings.append("OCR language differs from the configured language.")
        if not execution.text_extracted:
            confidence_valid = not strict
            if strict:
                warnings.append("OCR did not extract text.")
        else:
            confidence_valid = execution.confidence >= self.min_confidence
            if not confidence_valid:
                warnings.append("OCR confidence is below the configured minimum.")
        if strict and execution.status != "OCR_COMPLETED":
            warnings.append("Tesseract execution did not complete with text.")
        valid = not errors
        if strict:
            valid = valid and execution.status == "OCR_COMPLETED" and execution.text_extracted and language_valid and confidence_valid
        return OCRResultValidation(valid, tuple(dict.fromkeys(errors)), tuple(dict.fromkeys(warnings)), self.min_confidence, confidence_valid, language_valid)
