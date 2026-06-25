"""Vision Engine foundation."""

from __future__ import annotations

from predixai.capture import SnapshotMetadata
from predixai.core.config import AppConfig
from predixai.vision.frame import Frame
from predixai.vision.frame_storage import FrameStorage
from predixai.vision.frame_validator import FrameValidator
from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.image_loader import ImageLoader
from predixai.vision.roi_crop import ROICrop
from predixai.vision.roi_crop_engine import ROICropEngine
from predixai.vision.roi_crop_exporter import ROICropExporter
from predixai.vision.roi_crop_storage import ROICropExport, ROICropStorage
from predixai.vision.roi_manager import ROIManager
from predixai.vision.roi_registry import ROIRegistry


class VisionEngine:
    """Creates frame metadata without visual reading."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.validator = FrameValidator()
        self.storage = FrameStorage()
        self.image_loader = ImageLoader()
        self.roi_manager = ROIManager()
        self.roi_crop_engine = ROICropEngine()
        roi_output_directory = self.config.resolve_path("captures") / "rois"
        self.roi_crop_exporter = ROICropExporter(
            ROICropStorage(roi_output_directory)
        )

    def process_capture(self, snapshot: SnapshotMetadata) -> Frame:
        """Create one frame from a capture file path."""
        validation = self.validator.validate(snapshot.file_path)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        file_metadata = self.storage.load_metadata(snapshot.file_path)
        return Frame(
            session_id=snapshot.session_id,
            timestamp=snapshot.captured_at,
            filename=file_metadata.filename,
            width=validation.width,
            height=validation.height,
            file_size=file_metadata.file_size,
            sha256=file_metadata.sha256,
            image_format=validation.image_format,
        )

    def register_rois(self, frame: Frame) -> ROIRegistry:
        """Register default ROI metadata for future Vision steps."""
        return self.roi_manager.load_default_registry(frame)

    def load_image_buffer(self, snapshot: SnapshotMetadata) -> ImageBuffer:
        """Load PNG bytes and return image buffer metadata."""
        return self.image_loader.load(snapshot.file_path)

    def create_roi_crops(
        self,
        registry: ROIRegistry,
        image_buffer: ImageBuffer,
    ) -> tuple[ROICrop, ...]:
        """Create ROI crop metadata without extracting pixels."""
        return self.roi_crop_engine.create_crops(registry, image_buffer)

    def export_roi_crops(
        self,
        roi_crops: tuple[ROICrop, ...],
        image_buffer: ImageBuffer,
    ) -> tuple[ROICropExport, ...]:
        """Export ROI crop PNG files without interpreting image content."""
        return self.roi_crop_exporter.export_all(roi_crops, image_buffer)
