"""Screen environment inspection for the Perception Engine."""

from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenArea:
    """Rectangular screen area."""

    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        """Return a serializable representation."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class ScreenResolution:
    """Screen resolution in pixels."""

    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        """Return a serializable representation."""
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class ScreenEnvironment:
    """Detected screen environment."""

    operating_system: str
    resolution: ScreenResolution
    scale_percent: int
    monitor_count: int
    primary_monitor: str
    work_area: ScreenArea

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "operating_system": self.operating_system,
            "resolution": self.resolution.to_dict(),
            "scale_percent": self.scale_percent,
            "monitor_count": self.monitor_count,
            "primary_monitor": self.primary_monitor,
            "work_area": self.work_area.to_dict(),
        }


class ScreenEnvironmentDetector:
    """Detect basic screen environment metadata."""

    def inspect(self) -> ScreenEnvironment:
        """Inspect the current screen environment."""
        if platform.system() == "Windows":
            return self._inspect_windows()
        return self._inspect_generic()

    def _inspect_windows(self) -> ScreenEnvironment:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        monitor_count = int(user32.GetSystemMetrics(80))
        scale_percent = _get_windows_scale_percent()
        work_area = _get_windows_work_area(user32)

        return ScreenEnvironment(
            operating_system=platform.platform(),
            resolution=ScreenResolution(width=width, height=height),
            scale_percent=scale_percent,
            monitor_count=monitor_count,
            primary_monitor="Primary Monitor",
            work_area=work_area,
        )

    def _inspect_generic(self) -> ScreenEnvironment:
        return ScreenEnvironment(
            operating_system=platform.platform(),
            resolution=ScreenResolution(width=0, height=0),
            scale_percent=100,
            monitor_count=0,
            primary_monitor="unknown",
            work_area=ScreenArea(left=0, top=0, width=0, height=0),
        )


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _get_windows_work_area(user32: ctypes.WinDLL) -> ScreenArea:
    rect = _Rect()
    success = user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    if not success:
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        return ScreenArea(left=0, top=0, width=width, height=height)

    return ScreenArea(
        left=int(rect.left),
        top=int(rect.top),
        width=int(rect.right - rect.left),
        height=int(rect.bottom - rect.top),
    )


def _get_windows_scale_percent() -> int:
    user32 = ctypes.windll.user32
    try:
        dpi = int(user32.GetDpiForSystem())
    except AttributeError:
        dpi = _get_windows_device_dpi(user32)
    return max(1, round(dpi / 96 * 100))


def _get_windows_device_dpi(user32: ctypes.WinDLL) -> int:
    gdi32 = ctypes.windll.gdi32
    hdc = user32.GetDC(None)
    if not hdc:
        return 96
    try:
        return int(gdi32.GetDeviceCaps(hdc, 88))
    finally:
        user32.ReleaseDC(None, hdc)
