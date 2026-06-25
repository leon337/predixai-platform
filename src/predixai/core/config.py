"""Configuration loading for the PredixAI foundation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


@dataclass(frozen=True)
class AppConfig:
    """Loaded application configuration."""

    path: Path
    values: dict[str, Any]

    @property
    def application(self) -> dict[str, Any]:
        return self._section("application")

    @property
    def name(self) -> str:
        return str(self.application["name"])

    @property
    def version(self) -> str:
        return str(self.application["version"])

    @property
    def mode(self) -> str:
        return str(self.application["mode"])

    @property
    def environment(self) -> str:
        return str(self.application["environment"])

    @property
    def paths(self) -> dict[str, str]:
        paths = self._section("paths")
        return {str(key): str(value) for key, value in paths.items()}

    @property
    def logging(self) -> dict[str, Any]:
        return self._section("logging")

    @property
    def perception(self) -> dict[str, Any]:
        return self._section("perception")

    @property
    def window_detection(self) -> dict[str, Any]:
        return self._section("window_detection")

    @property
    def screen_profile(self) -> dict[str, Any]:
        return self._section("screen_profile")

    @property
    def capture(self) -> dict[str, Any]:
        return self._section("capture")

    @property
    def vision(self) -> dict[str, Any]:
        return self._section("vision")

    @property
    def ocr(self) -> dict[str, Any]:
        return self._section("ocr")

    @property
    def v1_modules(self) -> tuple[dict[str, str], ...]:
        modules = self._section("modules").get("v1", [])
        if not isinstance(modules, list):
            raise ValueError("Config key modules.v1 must be a list.")

        normalized: list[dict[str, str]] = []
        for module in modules:
            if not isinstance(module, dict):
                raise ValueError("Each module entry must be an object.")
            normalized.append(
                {
                    "name": str(module["name"]),
                    "package": str(module["package"]),
                }
            )
        return tuple(normalized)

    def resolve_path(self, key: str) -> Path:
        """Resolve a configured project path."""
        try:
            raw_path = self.paths[key]
        except KeyError as exc:
            raise KeyError(f"Missing configured path: {key}") from exc

        path = Path(raw_path)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    def resolve_project_path(self, raw_path: str | Path) -> Path:
        """Resolve a path relative to the project root."""
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    def _section(self, key: str) -> dict[str, Any]:
        section = self.values.get(key)
        if not isinstance(section, dict):
            raise KeyError(f"Missing or invalid config section: {key}")
        return section


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load and validate the application config file."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        values = json.load(file)

    if not isinstance(values, dict):
        raise ValueError("Config root must be a JSON object.")

    return AppConfig(path=path, values=values)
