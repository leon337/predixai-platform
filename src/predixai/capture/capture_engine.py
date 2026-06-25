"""Capture Engine foundation bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from predixai.capture.capture_session import CaptureSession
from predixai.capture.capture_snapshot import ManualScreenSnapshot
from predixai.capture.capture_storage import CaptureStorage
from predixai.capture.capture_validator import CaptureValidator
from predixai.capture.snapshot_metadata import SnapshotMetadata
from predixai.core.config import AppConfig


@dataclass(frozen=True)
class CaptureEngineStatus:
    """Capture Engine bootstrap status."""

    enabled: bool
    session: CaptureSession
    storage: CaptureStorage


class CaptureEngine:
    """Initializes screenshot capture infrastructure without capturing."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.validator = CaptureValidator()
        self.snapshot = ManualScreenSnapshot()

    def bootstrap(self) -> CaptureEngineStatus:
        """Validate capture configuration and create a unique session."""
        storage = CaptureStorage.from_config(self.config)
        validation = self.validator.validate(storage)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return CaptureEngineStatus(
            enabled=bool(self.config.capture["enabled"]),
            session=CaptureSession(),
            storage=storage,
        )

    def capture_manual_snapshot(
        self,
        status: CaptureEngineStatus | None = None,
    ) -> SnapshotMetadata:
        """Capture one manual snapshot using an existing capture session."""
        active_status = status or self.bootstrap()
        captured_at = datetime.now().astimezone()
        output_path = active_status.storage.build_snapshot_path(captured_at)
        result = self.snapshot.capture(
            output_path=output_path,
            compression=active_status.storage.compression,
        )

        return SnapshotMetadata(
            session_id=active_status.session.session_id,
            captured_at=captured_at.isoformat(),
            resolution_width=result.width,
            resolution_height=result.height,
            file_path=output_path,
            file_size_bytes=result.file_size_bytes,
            image_format=active_status.storage.image_format,
        )
