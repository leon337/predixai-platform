"""ROI crop PNG export foundation."""

from __future__ import annotations

import shutil
from datetime import datetime

from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.roi_crop import ROICrop
from predixai.vision.roi_crop_storage import ROICropExport, ROICropStorage


class ROICropExporter:
    """Export FULL_SCREEN ROI PNG by reusing the original capture file."""

    def __init__(self, storage: ROICropStorage) -> None:
        self.storage = storage

    def export(
        self,
        roi_crop: ROICrop,
        image_buffer: ImageBuffer,
    ) -> ROICropExport:
        """Export a FULL_SCREEN ROI PNG without image interpretation."""
        self._validate_full_screen(roi_crop, image_buffer)
        output_path = self.storage.build_output_path(roi_crop)
        shutil.copyfile(image_buffer.file_path, output_path)

        return ROICropExport(
            roi_id=roi_crop.roi_id,
            roi_name=roi_crop.roi_name,
            source_frame=roi_crop.source_frame,
            output_path=output_path,
            file_size=output_path.stat().st_size,
            image_format=image_buffer.image_format,
            exported_at=datetime.now().astimezone().isoformat(),
            reused_source=True,
        )

    def export_all(
        self,
        roi_crops: tuple[ROICrop, ...],
        image_buffer: ImageBuffer,
    ) -> tuple[ROICropExport, ...]:
        """Export all ROI crops available for this phase."""
        return tuple(
            self.export(roi_crop, image_buffer)
            for roi_crop in roi_crops
        )

    def _validate_full_screen(
        self,
        roi_crop: ROICrop,
        image_buffer: ImageBuffer,
    ) -> None:
        if roi_crop.roi_id != "FULL_SCREEN":
            raise ValueError("Only FULL_SCREEN ROI export is available.")
        if roi_crop.x != 0 or roi_crop.y != 0:
            raise ValueError("FULL_SCREEN ROI must start at x=0 and y=0.")
        if roi_crop.width != image_buffer.width:
            raise ValueError("FULL_SCREEN ROI width must match the image width.")
        if roi_crop.height != image_buffer.height:
            raise ValueError("FULL_SCREEN ROI height must match the image height.")
