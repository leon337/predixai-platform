"""Build complete visual snapshots."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.frame import Frame
from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.regions import RegionRegistry
from predixai.vision.roi_crop_storage import ROICropExport
from predixai.vision.visual.structured_ocr_result import StructuredOCRResult
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class VisualSnapshotBuilder:
    """Create a complete structured visual snapshot."""

    def build(
        self,
        frame: Frame,
        image_buffer: ImageBuffer,
        region_registry: RegionRegistry,
        roi_exports: tuple[ROICropExport, ...],
        structured_ocr: StructuredOCRResult,
    ) -> VisualSnapshot:
        """Build one visual snapshot for the processed capture."""
        created_at = datetime.now().astimezone().isoformat()
        return VisualSnapshot(
            id=f"visual_snapshot:{frame.sha256}",
            session_id=frame.session_id,
            captured_at=frame.timestamp,
            created_at=created_at,
            source_frame=frame.filename,
            frame_sha256=frame.sha256,
            width=frame.width,
            height=frame.height,
            structured_ocr=structured_ocr,
            regions=region_registry.to_dict(),
            roi_exports=tuple(
                roi_export.to_dict() for roi_export in roi_exports
            ),
            metadata={
                "image_buffer": image_buffer.to_dict(),
                "region_count": region_registry.count,
                "roi_export_count": len(roi_exports),
                "structured_region_count": structured_ocr.total_regions,
                "structured_block_count": structured_ocr.total_blocks,
            },
        )
