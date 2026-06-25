"""Application bootstrap for the PredixAI foundation."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from predixai.capture import CaptureEngine, CaptureEngineStatus, SnapshotMetadata
from predixai.core.config import AppConfig, load_config
from predixai.core.events import EventRegistry
from predixai.core.logger import (
    configure_logger,
    log_capture_engine,
    log_error,
    log_image_buffer,
    log_manual_snapshot,
    log_perception,
    log_roi_crop,
    log_roi_crop_export,
    log_roi_registry,
    log_startup,
    log_vision_frame,
)
from predixai.perception import PerceptionEngine
from predixai.vision import VisionEngine


@dataclass(frozen=True)
class ModuleInfo:
    """Registered module metadata."""

    name: str
    package: str
    loaded: bool


@dataclass(frozen=True)
class StartupReport:
    """Result of the foundation startup sequence."""

    app_name: str
    version: str
    mode: str
    environment: str
    started_at: str
    modules: tuple[str, ...]
    status: str


class PredixAIApp:
    """Coordinates the foundation startup without business functionality."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config: AppConfig = load_config(config_path)
        self.logger = configure_logger(self.config)
        self.events = EventRegistry()
        self.modules: tuple[ModuleInfo, ...] = ()
        self.capture_engine: CaptureEngine | None = None
        self.capture_status: CaptureEngineStatus | None = None
        self.vision_engine: VisionEngine | None = None

    def bootstrap(self) -> StartupReport:
        """Load foundation services and return a startup report."""
        try:
            self.modules = self._load_modules()
            module_names = tuple(module.name for module in self.modules)
            log_startup(self.logger, self.config, module_names)
            perception_snapshot = self._inspect_perception()
            capture_status = self._initialize_capture()
            self.events.record(
                "application.initialized",
                {
                    "version": self.config.version,
                    "mode": self.config.mode,
                    "modules": module_names,
                },
            )
            if perception_snapshot is not None:
                self.events.record(
                    "perception.environment_detected",
                    {
                        "environment": perception_snapshot.environment.to_dict(),
                        "window_count": len(perception_snapshot.windows.windows),
                    },
                )
            if capture_status is not None:
                self.events.record(
                    "capture.engine_initialized",
                    {
                        "session_id": capture_status.session.session_id,
                        "storage": capture_status.storage.to_dict(),
                    },
                )
            return StartupReport(
                app_name=self.config.name,
                version=self.config.version,
                mode=self.config.mode,
                environment=self.config.environment,
                started_at=datetime.now().astimezone().isoformat(),
                modules=module_names,
                status="initialized",
            )
        except Exception as exc:
            self.events.record("application.error", {"error": str(exc)})
            log_error(self.logger, "PredixAI initialization error", exc)
            raise

    def capture_snapshot(self) -> SnapshotMetadata:
        """Capture one manual snapshot after the foundation bootstrap."""
        if self.capture_engine is None or self.capture_status is None:
            capture_status = self._initialize_capture()
            if capture_status is None:
                raise RuntimeError("Capture Engine is disabled.")

        if self.capture_engine is None or self.capture_status is None:
            raise RuntimeError("Capture Engine is not available.")

        metadata = self.capture_engine.capture_manual_snapshot(
            self.capture_status
        )
        log_manual_snapshot(self.logger, metadata)
        self.events.record("capture.snapshot_created", metadata.to_dict())
        frame = self._process_vision_frame(metadata)
        if frame is not None:
            self.events.record("vision.frame_created", frame.to_dict())
        return metadata

    def _load_modules(self) -> tuple[ModuleInfo, ...]:
        loaded_modules: list[ModuleInfo] = []
        for module in self.config.v1_modules:
            importlib.import_module(module["package"])
            loaded_modules.append(
                ModuleInfo(
                    name=module["name"],
                    package=module["package"],
                    loaded=True,
                )
            )
        return tuple(loaded_modules)

    def _inspect_perception(self) -> object | None:
        if not bool(self.config.perception.get("enabled", False)):
            return None

        snapshot = PerceptionEngine(self.config).inspect()
        if bool(self.config.perception.get("log_on_startup", True)):
            log_perception(self.logger, snapshot)
        return snapshot

    def _initialize_capture(self) -> object | None:
        if not bool(self.config.capture.get("enabled", False)):
            return None

        self.capture_engine = CaptureEngine(self.config)
        status = self.capture_engine.bootstrap()
        self.capture_status = status
        log_capture_engine(self.logger, status)
        return status

    def _process_vision_frame(self, metadata: SnapshotMetadata) -> object | None:
        if not bool(self.config.vision.get("enabled", False)):
            return None

        if self.vision_engine is None:
            self.vision_engine = VisionEngine(self.config)

        frame = self.vision_engine.process_capture(metadata)
        log_vision_frame(self.logger, metadata, frame)
        image_buffer = self._load_vision_image_buffer(metadata)
        if image_buffer is not None:
            self.events.record("vision.image_buffer_created", image_buffer.to_dict())
        roi_registry = self._register_vision_rois(frame)
        if roi_registry is not None:
            self.events.record("vision.roi_registry_loaded", roi_registry.to_dict())
        if image_buffer is not None and roi_registry is not None:
            roi_crops = self._create_roi_crops(roi_registry, image_buffer)
            self.events.record(
                "vision.roi_crops_created",
                {"crops": [roi_crop.to_dict() for roi_crop in roi_crops]},
            )
            roi_exports = self._export_roi_crops(roi_crops, image_buffer)
            self.events.record(
                "vision.roi_crops_exported",
                {"exports": [roi_export.to_dict() for roi_export in roi_exports]},
            )
        return frame

    def _load_vision_image_buffer(self, metadata: SnapshotMetadata) -> object | None:
        image_loader_config = self.config.vision.get("image_loader", {})
        if not isinstance(image_loader_config, dict):
            return None
        if not bool(image_loader_config.get("enabled", False)):
            return None
        if self.vision_engine is None:
            return None

        image_buffer = self.vision_engine.load_image_buffer(metadata)
        log_image_buffer(self.logger, image_buffer)
        return image_buffer

    def _register_vision_rois(self, frame: object) -> object | None:
        roi_config = self.config.vision.get("roi", {})
        if not isinstance(roi_config, dict):
            return None
        if not bool(roi_config.get("enabled", False)):
            return None
        if self.vision_engine is None:
            return None

        registry = self.vision_engine.register_rois(frame)
        log_roi_registry(self.logger, registry)
        return registry

    def _create_roi_crops(
        self,
        roi_registry: object,
        image_buffer: object,
    ) -> tuple[object, ...]:
        if self.vision_engine is None:
            return ()

        roi_crops = self.vision_engine.create_roi_crops(
            roi_registry,
            image_buffer,
        )
        for roi_crop in roi_crops:
            log_roi_crop(self.logger, roi_crop)
        return roi_crops

    def _export_roi_crops(
        self,
        roi_crops: tuple[object, ...],
        image_buffer: object,
    ) -> tuple[object, ...]:
        if self.vision_engine is None:
            return ()

        roi_exports = self.vision_engine.export_roi_crops(
            roi_crops,
            image_buffer,
        )
        for roi_export in roi_exports:
            log_roi_crop_export(self.logger, roi_export)
        return roi_exports
