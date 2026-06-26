"""Detect the active broker or browser window."""

from __future__ import annotations

from ctypes import Structure, byref, c_int, create_unicode_buffer, windll
from datetime import datetime

from predixai.live.broker_window_state import BrokerWindowState


class _RECT(Structure):
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("right", c_int),
        ("bottom", c_int),
    ]


class BrokerWindowDetector:
    def detect(self) -> BrokerWindowState:
        user32 = windll.user32
        hwnd = user32.GetForegroundWindow()
        title = self._window_text(user32, hwnd)
        rect = _RECT()
        user32.GetWindowRect(hwnd, byref(rect))
        maximized = bool(user32.IsZoomed(hwnd))
        foreground = bool(user32.GetForegroundWindow() == hwnd)
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        return BrokerWindowState(
            title=title or "UNKNOWN",
            resolution_width=width,
            resolution_height=height,
            left=int(rect.left),
            top=int(rect.top),
            maximized=maximized,
            foreground=foreground,
            detected_at=datetime.now().astimezone().isoformat(),
            metadata={"detected": True},
        )

    def _window_text(self, user32: object, hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value.strip()
