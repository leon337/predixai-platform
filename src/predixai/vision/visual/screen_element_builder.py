"""Build screen elements from visual snapshots."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.screen_element import ScreenElement, ScreenElements
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class ScreenElementBuilder:
    """Create deterministic screen elements without AI classification."""

    def build(self, visual_snapshot: VisualSnapshot) -> ScreenElements:
        """Build screen elements from structured OCR regions."""
        created_at = datetime.now().astimezone().isoformat()
        elements = tuple(
            self._build_region_element(visual_snapshot, created_at, index, region)
            for index, region in enumerate(
                visual_snapshot.structured_ocr.regions,
                start=1,
            )
        )
        return ScreenElements(
            source_snapshot_id=visual_snapshot.id,
            source_frame=visual_snapshot.source_frame,
            created_at=created_at,
            elements=elements,
        )

    def _build_region_element(
        self,
        visual_snapshot: VisualSnapshot,
        created_at: str,
        index: int,
        region: object,
    ) -> ScreenElement:
        return ScreenElement(
            id=(
                "screen_element:"
                f"{visual_snapshot.frame_sha256}:{region.region_id}:{index}"
            ),
            element_type="STRUCTURED_OCR_REGION",
            source="structured_ocr",
            source_region_id=region.region_id,
            source_region_name=region.region_name,
            x=region.x,
            y=region.y,
            width=region.width,
            height=region.height,
            text=region.text,
            confidence=region.confidence,
            created_at=created_at,
            metadata={
                "source_snapshot_id": visual_snapshot.id,
                "source_frame": visual_snapshot.source_frame,
                "structured_ocr_id": visual_snapshot.structured_ocr.id,
                "block_count": region.block_count,
                "source_image_sha256": region.source_image_sha256,
                "ai_classification": False,
            },
        )
