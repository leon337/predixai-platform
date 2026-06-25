"""Vision Engine foundation."""

from __future__ import annotations

from predixai.capture import SnapshotMetadata
from predixai.core.config import AppConfig
from predixai.vision.frame import Frame
from predixai.vision.frame_storage import FrameStorage
from predixai.vision.frame_validator import FrameValidator


class VisionEngine:
    """Creates frame metadata without visual reading."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.validator = FrameValidator()
        self.storage = FrameStorage()

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
