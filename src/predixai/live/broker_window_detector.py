"""Detect the active broker or browser window."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from ctypes import Structure, byref, c_int, create_unicode_buffer
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence

if sys.platform.startswith("win"):
    from ctypes import windll
else:
    windll = None

from predixai.live.broker_window_state import BrokerWindowState


class _RECT(Structure):
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("right", c_int),
        ("bottom", c_int),
    ]


class BrokerWindowDetector:
    def __init__(
        self,
        *,
        command_runner: Callable[
            [Sequence[str]], subprocess.CompletedProcess[str]
        ] | None = None,
        process_name_reader: Callable[[int], str] | None = None,
    ) -> None:
        self._command_runner = command_runner or self._run_targeted_command
        self._process_name_reader = process_name_reader or self._read_process_name

    def detect(self) -> BrokerWindowState:
        detected_at = datetime.now().astimezone().isoformat()

        if windll is None:
            if sys.platform.startswith("linux"):
                return self._detect_linux(detected_at)
            return self._unsupported_platform(detected_at)

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
                "platform": sys.platform,
                "detector": "windows_ctypes",
            },
        )

    def _detect_linux(self, detected_at: str) -> BrokerWindowState:
        if shutil.which("wmctrl") is None:
            return self._unsupported_platform(
                detected_at,
                reason="wmctrl não instalado; detector Linux indisponível.",
            )

        windows = self._linux_windows()
        active_window_id = self._linux_active_window_id()

        if not windows:
            return BrokerWindowState(
                title="LINUX_NO_WINDOWS_FOUND",
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
                    "ignore_reason": "Nenhuma janela encontrada via wmctrl.",
                    "window_kind": "linux_no_windows",
                    "platform": sys.platform,
                    "detector": "linux_wmctrl",
                },
            )

        active_window = None
        for window in windows:
            if active_window_id is not None and window["id_int"] == active_window_id:
                active_window = window
                break

        valid_window = None
        for window in windows:
            validation = self._classify_title(window["title"])
            if validation["valid"]:
                valid_window = window
                break

        selected = valid_window or active_window or windows[0]
        validation = self._classify_title(selected["title"])
        foreground = active_window_id is not None and selected["id_int"] == active_window_id

        return BrokerWindowState(
            title=selected["title"] or "UNKNOWN",
            resolution_width=selected["width"],
            resolution_height=selected["height"],
            left=selected["left"],
            top=selected["top"],
            maximized=False,
            foreground=foreground,
            detected_at=detected_at,
            metadata={
                "detected": True,
                "broker_window_valid": validation["valid"],
                "ignored": not validation["valid"],
                "ignore_reason": validation["reason"],
                "window_kind": validation["kind"],
                "platform": sys.platform,
                "detector": "linux_wmctrl",
                "window_id": selected["id"],
                "active_window_id": hex(active_window_id) if active_window_id is not None else None,
            },
        )

    def inspect_explicit_linux_window(self, window_id: str) -> BrokerWindowState:
        """Inspect exactly one X11 client without enumerating or selecting fallbacks."""
        if not sys.platform.startswith("linux"):
            raise RuntimeError("explicit X11 inspection is available only on Linux")
        normalized = self._normalize_window_id(window_id)
        if not normalized:
            raise ValueError("explicit non-zero hexadecimal window ID is required")
        if shutil.which("xprop") is None or shutil.which("xwininfo") is None:
            raise RuntimeError("xprop and xwininfo are required for explicit X11 inspection")

        properties = self._command_runner(
            (
                "xprop",
                "-id",
                normalized,
                "_NET_WM_PID",
                "WM_CLASS",
                "_NET_WM_NAME",
                "WM_NAME",
                "_NET_WM_STATE",
            )
        )
        geometry_result = self._command_runner(
            ("xwininfo", "-id", normalized, "-stats", "-wm")
        )
        active_result = self._command_runner(
            ("xprop", "-root", "_NET_ACTIVE_WINDOW")
        )
        for label, result in (
            ("xprop-window", properties),
            ("xwininfo-window", geometry_result),
            ("xprop-active", active_result),
        ):
            if result.returncode != 0:
                raise RuntimeError(
                    f"{label} failed with return code {result.returncode}"
                )

        pid_match = re.search(r"_NET_WM_PID\(CARDINAL\)\s*=\s*(\d+)", properties.stdout)
        title_match = re.search(
            r'_NET_WM_NAME\([^)]*\)\s*=\s*"([^"]*)"',
            properties.stdout,
        )
        if title_match is None:
            title_match = re.search(
                r'WM_NAME\([^)]*\)\s*=\s*"([^"]*)"',
                properties.stdout,
            )
        if pid_match is None or title_match is None:
            raise RuntimeError("targeted X11 identity metadata is incomplete")
        pid = int(pid_match.group(1))
        process_name = self._process_name_reader(pid).strip()
        if not process_name:
            raise RuntimeError("targeted X11 process name is unavailable")

        def integer(label: str) -> int:
            match = re.search(
                rf"{re.escape(label)}:\s+(-?\d+)", geometry_result.stdout
            )
            if match is None:
                raise RuntimeError(f"targeted X11 geometry missing: {label}")
            return int(match.group(1))

        left = integer("Absolute upper-left X")
        top = integer("Absolute upper-left Y")
        width = integer("Width")
        height = integer("Height")
        if width <= 0 or height <= 0:
            raise RuntimeError("targeted X11 geometry is invalid")
        map_match = re.search(r"Map State:\s+([^\n]+)", geometry_result.stdout)
        if map_match is None:
            raise RuntimeError("targeted X11 map state is unavailable")
        visible = map_match.group(1).strip() == "IsViewable"
        minimized = "_NET_WM_STATE_HIDDEN" in properties.stdout or not visible
        active_match = re.search(
            r"#\s*(0x[0-9a-fA-F]+)", active_result.stdout
        )
        active_id = (
            self._normalize_window_id(active_match.group(1)) if active_match else ""
        )
        foreground = active_id == normalized
        detected_at = datetime.now().astimezone().isoformat()
        title = title_match.group(1)

        return BrokerWindowState(
            title=title,
            resolution_width=width,
            resolution_height=height,
            left=left,
            top=top,
            maximized=False,
            foreground=foreground,
            detected_at=detected_at,
            metadata={
                "detected": True,
                "detector": "linux_x11_explicit_window",
                "window_id": normalized,
                "window_pid": pid,
                "process_name": process_name,
                "window_visible": visible,
                "window_minimized": minimized,
                "active_window_id": active_id,
                "fallback_used": False,
            },
        )

    def _unsupported_platform(self, detected_at: str, reason: str | None = None) -> BrokerWindowState:
        return BrokerWindowState(
            title="WINDOW_DETECTION_UNAVAILABLE",
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
                "ignore_reason": reason or "Detecção automática de janela indisponível nesta plataforma.",
                "window_kind": "unsupported_platform",
                "platform": sys.platform,
            },
        )

    def _linux_windows(self) -> list[dict[str, object]]:
        result = subprocess.run(
            ["wmctrl", "-lG"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )

        windows: list[dict[str, object]] = []
        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=7)
            if len(parts) < 8:
                continue

            window_id, desktop, left, top, width, height, host, title = parts
            try:
                windows.append(
                    {
                        "id": window_id,
                        "id_int": int(window_id, 16),
                        "desktop": desktop,
                        "left": int(left),
                        "top": int(top),
                        "width": int(width),
                        "height": int(height),
                        "host": host,
                        "title": title.strip(),
                    }
                )
            except ValueError:
                continue

        return windows

    def _linux_active_window_id(self) -> int | None:
        if shutil.which("xprop") is None:
            return None

        result = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )

        match = re.search(r"#\s*(0x[0-9a-fA-F]+)", result.stdout)
        if not match:
            return None

        try:
            return int(match.group(1), 16)
        except ValueError:
            return None

    @staticmethod
    def _normalize_window_id(value: object) -> str:
        text = str(value or "").strip().lower()
        if not re.fullmatch(r"0x[0-9a-f]+", text):
            return ""
        numeric = int(text, 16)
        return hex(numeric) if numeric > 0 else ""

    @staticmethod
    def _run_targeted_command(
        command: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        allowed = (
            tuple(command[:2]) in {
                ("xprop", "-id"),
                ("xwininfo", "-id"),
                ("xprop", "-root"),
            }
            and "-root" not in command[2:]
        )
        if not allowed:
            raise ValueError(f"targeted X11 command is not allowlisted: {tuple(command)!r}")
        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=3.0,
        )

    @staticmethod
    def _read_process_name(pid: int) -> str:
        if pid <= 0:
            return ""
        path = Path("/proc") / str(pid) / "comm"
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return ""

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
            r"olymp\s*trade|olymptrade(?:\.com)?|iq\s*option|quotex|exnova|avalon|quadcode|"
            r"google\s+chrome|microsoft\s+edge|brave|firefox",
            text,
            flags=re.IGNORECASE,
        )
        asset_or_price_evidence = re.search(
            r"cafe[ií]na\s+index|asia\s+composite\s+index|latam\s+index|"
            r"\b\d{3,6}(?:[.,]\d{1,6})?\s+[A-Za-zÀ-ÿ ]{2,40}\s+Index\b",
            text,
            flags=re.IGNORECASE,
        )

        valid_patterns = (
            r"cafe[ií]na\s+index",
            r"asia\s+composite\s+index",
            r"latam\s+index",
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
