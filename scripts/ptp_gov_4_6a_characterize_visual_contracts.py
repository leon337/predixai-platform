#!/usr/bin/env python3
"""PTP-GOV.4.6A: characterize visual-source contracts without capture or OCR.

This validator is intentionally preflight-only.  It may inspect environment variables,
tool availability and X11 root metadata.  It never lists window titles, captures pixels,
starts a server or invokes an OCR provider.  Logical topology interpretation is delegated
to the functional X11 topology component.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from predixai.capture.x11_display_topology import (  # noqa: E402
    X11DisplayTopology,
    derive_topology,
)


PTP_ID = "PTP-GOV.4.6A"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

AUTHORIZED_WINDOW_CONTRACT_FIELDS = (
    "AUTHORIZED_WINDOW_ID",
    "AUTHORIZED_WINDOW_PID",
    "AUTHORIZED_PROCESS_NAME",
    "AUTHORIZED_TITLE_PATTERN",
    "AUTHORIZED_GEOMETRY",
    "DISPLAY_SERVER",
    "WINDOW_VISIBLE",
    "WINDOW_MINIMIZED",
    "WINDOW_FOREGROUND",
    "GEOMETRY_STABLE",
    "SOURCE_CONFIRMED",
)

OBSERVATION_FIELDS = (
    "OBSERVED_WINDOW_ID",
    "OBSERVED_WINDOW_PID",
    "OBSERVED_PROCESS_NAME",
    "OBSERVED_TITLE",
    "OBSERVED_GEOMETRY",
    "DISPLAY_SERVER",
    "WINDOW_VISIBLE",
    "WINDOW_MINIMIZED",
    "WINDOW_FOREGROUND",
    "GEOMETRY_STABLE",
    "SOURCE_CONFIRMED",
    "DISPLAY_TOPOLOGY",
    "DISPLAY_TOPOLOGY_STABLE",
    "EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION",
    "CAPTURE_TARGET_MODE",
)

PROHIBITED_PROCESS_NAMES = {
    "code",
    "code-insiders",
    "codex",
    "xfce4-terminal",
    "gnome-terminal",
    "konsole",
    "xterm",
    "kitty",
    "alacritty",
    "bash",
    "zsh",
    "pwsh",
    "powershell",
}

PROHIBITED_TITLE_PATTERNS = (
    r"\bvisual studio code\b",
    r"\bcodex\b",
    r"\bterminal\b",
    r"\bpowershell\b",
    r"\bcommand prompt\b",
)

CAPTURE_TOOL_NAMES = (
    "xwd",
    "import",
    "scrot",
    "gnome-screenshot",
    "grim",
    "slurp",
    "spectacle",
    "maim",
)

METADATA_TOOL_NAMES = (
    "wmctrl",
    "xprop",
    "xwininfo",
)

ALLOWED_METADATA_COMMANDS = (
    ("wmctrl", "-m"),
    ("xprop", "-root", "_NET_ACTIVE_WINDOW", "_NET_CLIENT_LIST_STACKING"),
    ("xwininfo", "-root", "-stats"),
)

PROHIBITED_EXECUTABLES = {
    "xwd",
    "import",
    "scrot",
    "gnome-screenshot",
    "grim",
    "slurp",
    "spectacle",
    "maim",
    "tesseract",
}


def _normalized_window_id(value: Any) -> str:
    if isinstance(value, int) and value > 0:
        return hex(value)
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"0x[0-9a-f]+", text):
        return ""
    try:
        return hex(int(text, 16))
    except ValueError:
        return ""


def _valid_pid(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _normalized_geometry(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    expected = {"x", "y", "width", "height"}
    if set(value) != expected:
        return None
    if any(not isinstance(value[key], int) or isinstance(value[key], bool) for key in expected):
        return None
    geometry = {key: int(value[key]) for key in ("x", "y", "width", "height")}
    if geometry["width"] <= 0 or geometry["height"] <= 0:
        return None
    return geometry


def _prohibited_process(process_name: Any) -> bool:
    name = Path(str(process_name or "").strip()).name.casefold()
    return not name or name in PROHIBITED_PROCESS_NAMES


def _prohibited_title(title: Any) -> bool:
    text = str(title or "").strip()
    if not text:
        return True
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in PROHIBITED_TITLE_PATTERNS)


def _bool_is(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def _logical_topology_reasons(observation: Mapping[str, Any]) -> tuple[str, ...]:
    raw = observation.get("DISPLAY_TOPOLOGY")
    if not isinstance(raw, Mapping):
        return ("DISPLAY_TOPOLOGY_MISSING_OR_INVALID",)
    topology = X11DisplayTopology.from_values(raw)
    values = topology.values
    reasons: list[str] = []
    if values.get("LOGICAL_DESKTOP_COUNT") != 1:
        reasons.append("LOGICAL_DESKTOP_COUNT_NOT_ONE")
    if values.get("CAPTURE_SURFACE_COUNT") != 1:
        reasons.append("CAPTURE_SURFACE_COUNT_NOT_ONE")
    if values.get("EXTENDED_DESKTOP") != "NO":
        reasons.append("EXTENDED_DESKTOP_NOT_ALLOWED")
    if values.get("OUTPUTS_DO_NOT_EXPAND_ROOT_DESKTOP") != "YES":
        reasons.append("OUTPUTS_EXPAND_ROOT_DESKTOP")
    if not topology.gate_pass:
        reasons.append("LOGICAL_TOPOLOGY_GATE_FAILED")
    contradictions = set(values.get("CONTRADICTIONS") or ())
    if "PANNING_DECLARED" in contradictions:
        reasons.append("PANNING_NOT_ALLOWED")
    if "NON_IDENTITY_TRANSFORM" in contradictions:
        reasons.append("NON_IDENTITY_TRANSFORM_NOT_ALLOWED")
    if observation.get("DISPLAY_TOPOLOGY_STABLE") != "YES":
        reasons.append("DISPLAY_TOPOLOGY_NOT_STABLE")
    if observation.get("EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION") != "PASS":
        reasons.append("EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION_NOT_CONFIRMED")
    return tuple(dict.fromkeys(reasons))


def evaluate_capture_gate(
    contract: Mapping[str, Any],
    observation: Mapping[str, Any],
    *,
    backend_requires_foreground: bool = True,
) -> dict[str, Any]:
    """Evaluate an explicit authorized-window observation and fail closed."""
    reasons: list[str] = []

    for field in AUTHORIZED_WINDOW_CONTRACT_FIELDS:
        if field not in contract:
            reasons.append(f"CONTRACT_FIELD_MISSING:{field}")
    for field in OBSERVATION_FIELDS:
        if field not in observation:
            reasons.append(f"OBSERVATION_FIELD_MISSING:{field}")

    authorized_id = _normalized_window_id(contract.get("AUTHORIZED_WINDOW_ID"))
    observed_id = _normalized_window_id(observation.get("OBSERVED_WINDOW_ID"))
    if not authorized_id:
        reasons.append("AUTHORIZED_WINDOW_ID_INVALID")
    if not observed_id or observed_id != authorized_id:
        reasons.append("WINDOW_ID_MISMATCH")

    authorized_pid = contract.get("AUTHORIZED_WINDOW_PID")
    observed_pid = observation.get("OBSERVED_WINDOW_PID")
    if not _valid_pid(authorized_pid):
        reasons.append("AUTHORIZED_WINDOW_PID_INVALID")
    if not _valid_pid(observed_pid) or observed_pid != authorized_pid:
        reasons.append("WINDOW_PID_MISMATCH")

    authorized_process = str(contract.get("AUTHORIZED_PROCESS_NAME") or "").strip()
    observed_process = str(observation.get("OBSERVED_PROCESS_NAME") or "").strip()
    if _prohibited_process(authorized_process):
        reasons.append("AUTHORIZED_PROCESS_PROHIBITED")
    if not observed_process or observed_process.casefold() != authorized_process.casefold():
        reasons.append("PROCESS_NAME_MISMATCH")

    title_pattern = str(contract.get("AUTHORIZED_TITLE_PATTERN") or "")
    observed_title = str(observation.get("OBSERVED_TITLE") or "")
    try:
        title_matches = bool(title_pattern and re.fullmatch(title_pattern, observed_title))
    except re.error:
        title_matches = False
        reasons.append("AUTHORIZED_TITLE_PATTERN_INVALID")
    if _prohibited_title(observed_title):
        reasons.append("OBSERVED_TITLE_PROHIBITED")
    if not title_matches:
        reasons.append("TITLE_PATTERN_MISMATCH")

    authorized_geometry = _normalized_geometry(contract.get("AUTHORIZED_GEOMETRY"))
    observed_geometry = _normalized_geometry(observation.get("OBSERVED_GEOMETRY"))
    if authorized_geometry is None:
        reasons.append("AUTHORIZED_GEOMETRY_INVALID")
    if observed_geometry is None or observed_geometry != authorized_geometry:
        reasons.append("GEOMETRY_MISMATCH")

    display_server = str(contract.get("DISPLAY_SERVER") or "").strip().upper()
    observed_display_server = str(observation.get("DISPLAY_SERVER") or "").strip().upper()
    if display_server not in {"X11", "WAYLAND"}:
        reasons.append("DISPLAY_SERVER_UNSUPPORTED")
    if observed_display_server != display_server:
        reasons.append("DISPLAY_SERVER_MISMATCH")

    if not _bool_is(contract.get("WINDOW_VISIBLE"), True):
        reasons.append("CONTRACT_REQUIRES_VISIBLE_WINDOW")
    if not _bool_is(observation.get("WINDOW_VISIBLE"), True):
        reasons.append("WINDOW_NOT_VISIBLE")
    if not _bool_is(contract.get("WINDOW_MINIMIZED"), False):
        reasons.append("CONTRACT_REQUIRES_NOT_MINIMIZED")
    if not _bool_is(observation.get("WINDOW_MINIMIZED"), False):
        reasons.append("WINDOW_MINIMIZED")

    if backend_requires_foreground:
        if not _bool_is(contract.get("WINDOW_FOREGROUND"), True):
            reasons.append("CONTRACT_REQUIRES_FOREGROUND")
        if not _bool_is(observation.get("WINDOW_FOREGROUND"), True):
            reasons.append("WINDOW_NOT_FOREGROUND")

    if not _bool_is(contract.get("GEOMETRY_STABLE"), True):
        reasons.append("CONTRACT_REQUIRES_STABLE_GEOMETRY")
    if not _bool_is(observation.get("GEOMETRY_STABLE"), True):
        reasons.append("GEOMETRY_NOT_STABLE")
    if not _bool_is(contract.get("SOURCE_CONFIRMED"), True):
        reasons.append("CONTRACT_SOURCE_NOT_CONFIRMED")
    if not _bool_is(observation.get("SOURCE_CONFIRMED"), True):
        reasons.append("SOURCE_NOT_CONFIRMED")

    reasons.extend(_logical_topology_reasons(observation))
    if observation.get("CAPTURE_TARGET_MODE") != "EXPLICIT_WINDOW_ID":
        reasons.append("EXPLICIT_WINDOW_TARGET_REQUIRED")
    if contract.get("FULL_SCREEN_FALLBACK") != "PROHIBITED":
        reasons.append("FULL_SCREEN_FALLBACK_MUST_BE_PROHIBITED")

    unique_reasons = tuple(dict.fromkeys(reasons))
    capture_allowed = not unique_reasons
    return {
        "CAPTURE_ALLOWED": "YES" if capture_allowed else "NO",
        "CAPTURE_EXECUTED": "NO",
        "OCR_EXECUTED": "NO",
        "INVALID_READING_PUBLISHED": "NO",
        "LAST_VALID_READING_PRESERVED": "YES",
        "SOURCE_STATE": (
            "SOURCE_CONFIRMED"
            if capture_allowed
            else "WAITING_SOURCE_OR_SOURCE_NOT_CONFIRMED"
        ),
        "FAIL_CLOSED": "YES",
        "REASONS": unique_reasons,
    }


def validate_synthetic_png(image_path: str | Path) -> dict[str, Any]:
    """Validate only the PNG signature and IHDR dimensions of a synthetic fixture."""
    path = Path(image_path)
    data = path.read_bytes() if path.is_file() else b""
    valid = len(data) >= 24 and data.startswith(PNG_SIGNATURE)
    width = height = 0
    if valid:
        width, height = struct.unpack(">II", data[16:24])
        valid = width > 0 and height > 0
    return {
        "SYNTHETIC_IMAGE_VALID": "YES" if valid else "NO",
        "WIDTH": width,
        "HEIGHT": height,
        "OCR_EXECUTED": "NO",
        "CAPTURE_EXECUTED": "NO",
    }


def _safe_metadata_run(command: Sequence[str]) -> dict[str, Any]:
    command_tuple = tuple(command)
    if command_tuple not in ALLOWED_METADATA_COMMANDS:
        raise ValueError("metadata command is not allowlisted")
    if Path(command_tuple[0]).name in PROHIBITED_EXECUTABLES:
        raise ValueError("capture or OCR executable is prohibited in PTP-GOV.4.6A")
    try:
        completed = subprocess.run(
            list(command_tuple),
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "returncode": None, "error": type(exc).__name__}
    return {
        "available": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def characterize_environment(
    *,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    command_runner: Callable[[Sequence[str]], dict[str, Any]] = _safe_metadata_run,
) -> dict[str, Any]:
    """Characterize local visual metadata capabilities without capturing pixels."""
    env = dict(os.environ if environ is None else environ)
    declared_session = str(env.get("XDG_SESSION_TYPE") or "").strip().lower()
    if declared_session == "x11":
        display_server = "X11"
    elif declared_session == "wayland":
        display_server = "WAYLAND"
    else:
        display_server = "UNKNOWN"

    tools = {
        name: {"available": bool(which(name)), "path": which(name) or "NOT_AVAILABLE"}
        for name in (*METADATA_TOOL_NAMES, *CAPTURE_TOOL_NAMES)
    }
    metadata_results: dict[str, Any] = {}
    for command in ALLOWED_METADATA_COMMANDS:
        if tools[command[0]]["available"]:
            metadata_results[" ".join(command)] = command_runner(command)
        else:
            metadata_results[" ".join(command)] = {
                "available": False,
                "returncode": None,
                "error": "TOOL_NOT_AVAILABLE",
            }

    metadata_ready = (
        display_server == "X11"
        and all(tools[name]["available"] for name in METADATA_TOOL_NAMES)
        and all(result.get("available") for result in metadata_results.values())
    )
    xwd_available = tools["xwd"]["available"]
    if display_server == "X11" and xwd_available:
        direct_capture_capability = "AVAILABLE_NOT_EXECUTED_XWD_EXPLICIT_WINDOW_ID"
    else:
        direct_capture_capability = "BLOCKED_NO_CONFIRMED_EXPLICIT_WINDOW_BACKEND"

    return {
        "PTP": PTP_ID,
        "PREFLIGHT_ONLY": "YES",
        "DISPLAY_SERVER": display_server,
        "XDG_SESSION_TYPE": declared_session or "NOT_DECLARED",
        "DISPLAY": env.get("DISPLAY") or "NOT_DECLARED",
        "WAYLAND_DISPLAY": env.get("WAYLAND_DISPLAY") or "NOT_DECLARED",
        "DESKTOP_SESSION": env.get("DESKTOP_SESSION") or "NOT_DECLARED",
        "XDG_CURRENT_DESKTOP": env.get("XDG_CURRENT_DESKTOP") or "NOT_DECLARED",
        "TOOLS": tools,
        "METADATA_COMMAND_RESULTS": metadata_results,
        "WINDOW_METADATA_CAPABILITY": (
            "PASS_METADATA_ONLY_NOT_SOURCE_AUTHORIZATION"
            if metadata_ready
            else "BLOCKED_METADATA_TOOLCHAIN"
        ),
        "DIRECT_WINDOW_CAPTURE_CAPABILITY": direct_capture_capability,
        "DIRECT_WINDOW_CAPTURE_EXECUTED": "NO",
        "OVERLAP_DETECTION_CAPABILITY": "NOT_PROVABLE_FROM_METADATA_FAIL_CLOSED",
        "FULL_SCREEN_FALLBACK": "PROHIBITED",
        "ACTIVE_WINDOW_GENERIC_FALLBACK": "PROHIBITED",
        "CAPTURE_EXECUTED": "NO",
        "OCR_EXECUTED": "NO",
        "SERVER_STARTED": "NO",
        "BROKER_OPENED": "NO",
        "REAL_RUNTIME_USED": "NO",
    }


def build_example_contract() -> dict[str, Any]:
    return {
        "AUTHORIZED_WINDOW_ID": "0x4200001",
        "AUTHORIZED_WINDOW_PID": 4242,
        "AUTHORIZED_PROCESS_NAME": "broker-browser",
        "AUTHORIZED_TITLE_PATTERN": r"Broker Simulado - [A-Z ]+",
        "AUTHORIZED_GEOMETRY": {"x": 0, "y": 0, "width": 1366, "height": 768},
        "DISPLAY_SERVER": "X11",
        "WINDOW_VISIBLE": True,
        "WINDOW_MINIMIZED": False,
        "WINDOW_FOREGROUND": True,
        "GEOMETRY_STABLE": True,
        "SOURCE_CONFIRMED": True,
        "FULL_SCREEN_FALLBACK": "PROHIBITED",
    }


def build_example_observation() -> dict[str, Any]:
    return {
        "OBSERVED_WINDOW_ID": "0x4200001",
        "OBSERVED_WINDOW_PID": 4242,
        "OBSERVED_PROCESS_NAME": "broker-browser",
        "OBSERVED_TITLE": "Broker Simulado - ATIVO TESTE",
        "OBSERVED_GEOMETRY": {"x": 0, "y": 0, "width": 1366, "height": 768},
        "DISPLAY_SERVER": "X11",
        "WINDOW_VISIBLE": True,
        "WINDOW_MINIMIZED": False,
        "WINDOW_FOREGROUND": True,
        "GEOMETRY_STABLE": True,
        "SOURCE_CONFIRMED": True,
        "DISPLAY_TOPOLOGY": {
            "LOGICAL_DESKTOP_COUNT": 1,
            "CAPTURE_SURFACE_COUNT": 1,
            "OUTPUT_LAYOUT_MODE": "MIRRORED_OR_CLONED",
            "EXTENDED_DESKTOP": "NO",
            "OUTPUTS_DO_NOT_EXPAND_ROOT_DESKTOP": "YES",
            "PANNING": {"LVDS-1": "NONE_DECLARED", "VGA-1-1": "NONE_DECLARED"},
            "TRANSFORM": {"LVDS-1": "IDENTITY", "VGA-1-1": "IDENTITY"},
            "CONTRADICTIONS": (),
            "TOPOLOGY_GATE_PASS": "YES",
        },
        "DISPLAY_TOPOLOGY_STABLE": "YES",
        "EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION": "PASS",
        "MONITOR_COUNT": 2,
        "ACTIVE_OUTPUT_COUNT": 2,
        "CONNECTED_OUTPUT_COUNT": 2,
        "CAPTURE_TARGET_MODE": "EXPLICIT_WINDOW_ID",
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="evaluate synthetic PASS and fail-closed contract objects",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = characterize_environment()
    if args.self_check:
        matching = evaluate_capture_gate(build_example_contract(), build_example_observation())
        invalid = build_example_observation()
        invalid["OBSERVED_PROCESS_NAME"] = "code"
        result["SYNTHETIC_MATCHING_CONTRACT"] = matching
        result["SYNTHETIC_FAIL_CLOSED_CONTRACT"] = evaluate_capture_gate(
            build_example_contract(), invalid
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key in (
            "PTP",
            "PREFLIGHT_ONLY",
            "DISPLAY_SERVER",
            "WINDOW_METADATA_CAPABILITY",
            "DIRECT_WINDOW_CAPTURE_CAPABILITY",
            "DIRECT_WINDOW_CAPTURE_EXECUTED",
            "OVERLAP_DETECTION_CAPABILITY",
            "FULL_SCREEN_FALLBACK",
            "CAPTURE_EXECUTED",
            "OCR_EXECUTED",
            "SERVER_STARTED",
            "BROKER_OPENED",
            "REAL_RUNTIME_USED",
        ):
            print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
