"""Detect the active broker or browser window."""

from __future__ import annotations

import re
import sys
from ctypes import Structure, byref, c_int, create_unicode_buffer

if sys.platform.startswith("win"):
    from ctypes import windll
else:
    windll = None
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
        detected_at = datetime.now().astimezone().isoformat()

        if windll is None:
            return BrokerWindowState(
                title="LINUX_WINDOW_DETECTION_UNAVAILABLE",
                resolution_width=0,
                resolution_height=0,
                left=0,
                top=0,
                maximized=False,
                foreground=False,
                detected_at=detected_at,
                metadata={
                    "detected": False,
                    "broker_window_valid": False,
                    "ignored": True,
                    "ignore_reason": "Detecção automática de janela via ctypes.windll disponível apenas no Windows.",
                    "window_kind": "linux_unsupported",
                    "platform": sys.platform,
                },
            )

        user32 = windll.user32
        hwnd = user32.GetForegroundWindow()
        title = self._window_text(user32, hwnd)
        rect = _RECT()
        user32.GetWindowRect(hwnd, byref(rect))
        maximized = bool(user32.IsZoomed(hwnd))
        foreground = bool(user32.GetForegroundWindow() == hwnd)
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        validation = self._classify_title(title)

        return BrokerWindowState(
            title=title or "UNKNOWN",
            resolution_width=width,
            resolution_height=height,
            left=int(rect.left),
            top=int(rect.top),
            maximized=maximized,
            foreground=foreground,
            detected_at=detected_at,
            metadata={
                "detected": True,
                "broker_window_valid": validation["valid"],
                "ignored": not validation["valid"],
                "ignore_reason": validation["reason"],
                "window_kind": validation["kind"],
            },
        )

    def _window_text(self, user32: object, hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value.strip()

    def _classify_title(self, title: str) -> dict[str, object]:
        text = (title or "").strip()
        lowered = text.lower()

        invalid_windows = (
            ("PowerShell", (r"powershell", r"\bpwsh\b")),
            ("VS Code", (r"visual studio code", r"\bcode\.exe\b")),
            ("Codex", (r"\bcodex\b",)),
            ("Mobile Server", (r"predixai\s+trader\s+mobile", r"\b/mobile\b", r"127\.0\.0\.1:8766", r"localhost:8766")),
            ("PredixAI Compact", (r"predixai\s+compact", r"predixai\s+trader")),
            ("dashboard", (r"\bdashboard\b", r"127\.0\.0\.1:8765", r"localhost:8765")),
            ("terminal", (r"\bterminal\b", r"cmd\.exe", r"command prompt", r"conhost")),
        )

        for kind, patterns in invalid_windows:
            if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns):
                return {
                    "valid": False,
                    "kind": kind,
                    "reason": f"Janela ignorada: {kind} não é corretora",
                }

        broker_evidence = re.search(
            r"olymp\s*trade|olymptrade(?:\.com)?|google\s+chrome|microsoft\s+edge",
            text,
            flags=re.IGNORECASE,
        )
        asset_or_price_evidence = re.search(
            r"cafe[ií]na\s+index|asia\s+composite\s+index|"
            r"\b\d{3,6}(?:[.,]\d{1,6})?\s+[A-Za-zÀ-ÿ ]{2,40}\s+Index\b",
            text,
            flags=re.IGNORECASE,
        )

        valid_patterns = (
            r"cafe[ií]na\s+index",
            r"asia\s+composite\s+index",
            r"\b\d{3,6}(?:[.,]\d{1,6})?\s+[A-Za-zÀ-ÿ ]{2,40}\s+Index\b",
        )
        if (
            broker_evidence
            and asset_or_price_evidence
            and any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in valid_patterns)
        ):
            return {
                "valid": True,
                "kind": "broker",
                "reason": "Janela válida de corretora detectada",
            }

        return {
            "valid": False,
            "kind": "unknown",
            "reason": "Janela ignorada: janela ativa não é corretora",
        }
