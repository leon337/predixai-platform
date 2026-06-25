"""Perception Engine foundation orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.core.config import AppConfig
from predixai.perception.calibration import CalibrationWizard
from predixai.perception.environment import (
    ScreenEnvironment,
    ScreenEnvironmentDetector,
)
from predixai.perception.screen_profile import (
    ScreenProfile,
    ScreenProfileRepository,
)
from predixai.perception.window_manager import (
    WindowDetectionResult,
    WindowManager,
)


@dataclass(frozen=True)
class PerceptionSnapshot:
    """Detected environment, windows and profile metadata."""

    environment: ScreenEnvironment
    windows: WindowDetectionResult
    screen_profile: ScreenProfile
    calibration: CalibrationWizard


class PerceptionEngine:
    """Coordinates perception foundation checks without visual reading."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.environment_detector = ScreenEnvironmentDetector()
        self.window_manager = WindowManager()

    def inspect(self) -> PerceptionSnapshot:
        """Inspect environment metadata and list current windows."""
        profile_path = self.config.resolve_project_path(
            str(self.config.screen_profile["default_profile"])
        )
        profile = ScreenProfileRepository(profile_path).load_default()
        window_config = self.config.window_detection
        windows = self.window_manager.list_windows(
            max_windows=int(window_config.get("max_windows", 100)),
            include_untitled=bool(window_config.get("include_untitled", False)),
        )

        return PerceptionSnapshot(
            environment=self.environment_detector.inspect(),
            windows=windows,
            screen_profile=profile,
            calibration=CalibrationWizard(),
        )
