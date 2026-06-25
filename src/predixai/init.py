"""Application factory for the PredixAI foundation."""

from __future__ import annotations

from pathlib import Path

from predixai.core.app import PredixAIApp


def create_application(config_path: str | Path | None = None) -> PredixAIApp:
    """Create a PredixAI application instance without starting business modules."""
    return PredixAIApp(config_path=config_path)
