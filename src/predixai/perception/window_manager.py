"""Window listing for the Perception Engine."""

from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class WindowInfo:
    """Top-level window metadata."""

    title: str
    x: int
    y: int
    width: int
    height: int
    active: bool

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "active": self.active,
        }


@dataclass(frozen=True)
class WindowDetectionResult:
    """Result of a window listing run."""

    windows: tuple[WindowInfo, ...]
    active_window: WindowInfo | None

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "windows": [window.to_dict() for window in self.windows],
            "active_window": (
                self.active_window.to_dict() if self.active_window else None
            ),
        }


class WindowManager:
    """List visible top-level windows without broker-specific detection."""

    def list_windows(
        self,
        max_windows: int = 100,
        include_untitled: bool = False,
    ) -> WindowDetectionResult:
        """List visible windows for the current operating system."""
        if platform.system() == "Windows":
            return self._list_windows_windows(max_windows, include_untitled)
        return WindowDetectionResult(windows=(), active_window=None)

    def _list_windows_windows(
        self,
        max_windows: int,
        include_untitled: bool,
    ) -> WindowDetectionResult:
        user32 = ctypes.windll.user32
        foreground = user32.GetForegroundWindow()
        windows: list[WindowInfo] = []

        def collect(hwnd: int, _: int) -> bool:
            if len(windows) >= max_windows:
                return False
            window = _read_window(user32, hwnd, foreground, include_untitled)
            if window is not None:
                windows.append(window)
            return True

        callback = _enum_windows_callback(collect)
        user32.EnumWindows(callback, 0)
        active_window = next((window for window in windows if window.active), None)
        return WindowDetectionResult(
            windows=tuple(windows),
            active_window=active_window,
        )


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _enum_windows_callback(
    callback: Callable[[int, int], bool],
) -> ctypes.WINFUNCTYPE:
    return ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )(lambda hwnd, lparam: callback(int(hwnd), int(lparam or 0)))


def _read_window(
    user32: ctypes.WinDLL,
    hwnd: int,
    foreground: int,
    include_untitled: bool,
) -> WindowInfo | None:
    if not user32.IsWindowVisible(hwnd):
        return None

    title = _get_window_title(user32, hwnd)
    if not title and not include_untitled:
        return None

    rect = _Rect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None

    return WindowInfo(
        title=title,
        x=int(rect.left),
        y=int(rect.top),
        width=width,
        height=height,
        active=hwnd == foreground,
    )


def _get_window_title(user32: ctypes.WinDLL, hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()
