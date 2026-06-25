"""Calibration Wizard architecture for future perception calibration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationWizard:
    """Future calibration wizard contract."""

    enabled: bool = False
    interface: str = "none"
