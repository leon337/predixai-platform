"""Application bootstrap for the PredixAI foundation."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from predixai.core.config import AppConfig, load_config
from predixai.core.events import EventRegistry
from predixai.core.logger import configure_logger, log_error, log_startup


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

    def bootstrap(self) -> StartupReport:
        """Load foundation services and return a startup report."""
        try:
            self.modules = self._load_modules()
            module_names = tuple(module.name for module in self.modules)
            log_startup(self.logger, self.config, module_names)
            self.events.record(
                "application.initialized",
                {
                    "version": self.config.version,
                    "mode": self.config.mode,
                    "modules": module_names,
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
