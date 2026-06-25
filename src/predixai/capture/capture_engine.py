"""Capture Engine foundation bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.capture.capture_session import CaptureSession
from predixai.capture.capture_storage import CaptureStorage
from predixai.capture.capture_validator import CaptureValidator
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
