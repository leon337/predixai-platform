"""OCR parser foundation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from predixai.ocr import OCRResult
from predixai.vision.visual.ocr_text_block import OCRTextBlock

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class OCRParsedText:
    """Structured representation of one OCRResult text payload."""

    source_image_sha256: str
    source_image_path: str
    provider: str
    language_used: str
    raw_text: str
    confidence: float
    parsed_at: str
    blocks: tuple[OCRTextBlock, ...]
    metadata: dict[str, Any]

    @property
    def block_count(self) -> int:
        """Return the number of parsed text blocks."""
        return len(self.blocks)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_image_sha256": self.source_image_sha256,
            "source_image_path": self.source_image_path,
            "provider": self.provider,
            "language_used": self.language_used,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "parsed_at": self.parsed_at,
            "block_count": self.block_count,
            "blocks": [block.to_dict() for block in self.blocks],
            "metadata": dict(self.metadata),
        }


class OCRParser:
    """Transform raw OCR text into structured text blocks."""

    def parse(self, ocr_result: OCRResult) -> OCRParsedText:
        """Parse one OCRResult without semantic interpretation."""
        parsed_at = datetime.now().astimezone().isoformat()
        raw_text = ocr_result.text if ocr_result.text_extracted else ""
        normalized_blocks = self._split_blocks(raw_text)
        blocks = tuple(
            OCRTextBlock(
                id=f"{ocr_result.image_sha256}:{index}",
                index=index,
                text=text,
                confidence=ocr_result.confidence,
                source_provider=ocr_result.provider,
                source_image_sha256=ocr_result.image_sha256,
                source_image_path=str(ocr_result.image_path),
                created_at=parsed_at,
                metadata={
                    "ocr_status": ocr_result.status,
                    "cache_hit": ocr_result.cache_hit,
                    "text_extraction_enabled": ocr_result.text_extraction_enabled,
                },
            )
            for index, text in enumerate(normalized_blocks, start=1)
        )

        return OCRParsedText(
            source_image_sha256=ocr_result.image_sha256,
            source_image_path=str(ocr_result.image_path),
            provider=ocr_result.provider,
            language_used=ocr_result.language_used,
            raw_text=raw_text,
            confidence=ocr_result.confidence,
            parsed_at=parsed_at,
            blocks=blocks,
            metadata={
                "ocr_status": ocr_result.status,
                "ocr_processing_time_ms": ocr_result.processing_time_ms,
                "ocr_benchmark": dict(ocr_result.benchmark),
            },
        )

    def _split_blocks(self, raw_text: str) -> tuple[str, ...]:
        lines = [
            self._normalize(line)
            for line in raw_text.splitlines()
            if self._normalize(line)
        ]
        if lines:
            return tuple(lines)

        normalized = self._normalize(raw_text)
        return (normalized,) if normalized else ()

    def _normalize(self, text: str) -> str:
        return _WHITESPACE.sub(" ", text).strip()
