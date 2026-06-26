"""Build structured OCR results."""

from __future__ import annotations

from datetime import datetime

from predixai.ocr import OCRResult
from predixai.vision.frame import Frame
from predixai.vision.visual.region_text_mapper import RegionTextMapping
from predixai.vision.visual.structured_ocr_result import StructuredOCRResult


class StructuredOCRBuilder:
    """Create a unified structured OCR result from mapped region text."""

    def build(
        self,
        frame: Frame,
        mapping: RegionTextMapping,
        ocr_results: tuple[OCRResult, ...],
    ) -> StructuredOCRResult:
        """Build one structured OCR result for the frame."""
        created_at = datetime.now().astimezone().isoformat()
        combined_text = " ".join(
            region_text.text
            for region_text in mapping.texts
            if region_text.text
        )
        total_blocks = sum(region_text.block_count for region_text in mapping.texts)
        average_confidence = self._average_confidence(mapping)

        return StructuredOCRResult(
            id=f"structured_ocr:{frame.sha256}",
            source_frame=frame.filename,
            created_at=created_at,
            regions=mapping.texts,
            combined_text=combined_text,
            average_confidence=average_confidence,
            total_regions=mapping.count,
            total_blocks=total_blocks,
            metadata={
                "frame_sha256": frame.sha256,
                "frame_width": frame.width,
                "frame_height": frame.height,
                "ocr_providers": sorted(
                    {ocr_result.provider for ocr_result in ocr_results}
                ),
                "ocr_languages": sorted(
                    {
                        ocr_result.language_used
                        for ocr_result in ocr_results
                        if ocr_result.language_used
                    }
                ),
                "ocr_statuses": [
                    ocr_result.status for ocr_result in ocr_results
                ],
                "ocr_cache_hits": [
                    ocr_result.cache_hit for ocr_result in ocr_results
                ],
            },
        )

    def _average_confidence(self, mapping: RegionTextMapping) -> float:
        confidences = [
            region_text.confidence
            for region_text in mapping.texts
            if region_text.confidence >= 0
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 3)
