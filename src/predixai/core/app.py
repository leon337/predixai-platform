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
    log_manual_snapshot,
    log_perception,
    log_startup,
)
from predixai.perception import PerceptionEngine


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
