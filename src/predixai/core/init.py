"""Core bootstrap helpers."""

from __future__ import annotations

from pathlib import Path

from predixai.core.app import PredixAIApp, StartupReport


def initialize_core(config_path: str | Path | None = None) -> StartupReport:
    """Initialize Core services and return the startup report."""
    app = PredixAIApp(config_path=config_path)
    return app.bootstrap()
