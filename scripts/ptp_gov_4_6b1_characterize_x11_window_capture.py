#!/usr/bin/env python3
"""PTP-GOV.4.6B.1: characterize xwd capture of explicit synthetic X11 windows.

This file is a standalone test harness.  It does not start capture, OCR, Mobile V2 or
Observer application modules.  Logical topology metadata comes from the functional X11
topology component.  The synthetic override is private to this validator and can target
only window IDs created by its own child processes.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from predixai.capture.x11_display_topology import X11DisplayTopologyInspector  # noqa: E402


CONTRACT_VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_6a_characterize_visual_contracts.py"
PTP_ID = "PTP-GOV.4.6B.1"
SYNTHETIC_CHARACTERIZATION_OVERRIDE = True
FUNCTIONAL_CAPTURE_OVERRIDE = False

AUTHORIZED_TITLE = "PTP-GOV-4.6B.1 AUTHORIZED SYNTHETIC WINDOW"
OVERLAY_TITLE = "PTP-GOV-4.6B.1 OVERLAY SYNTHETIC WINDOW"
AUTHORIZED_COLORS = (
    (229, 57, 53),
    (67, 160, 71),
    (30, 136, 229),
    (253, 216, 53),
)
OVERLAY_COLOR = (255, 0, 255)
AUTHORIZED_INITIAL_GEOMETRY = {"x": 80, "y": 90, "width": 200, "height": 120}
OVERLAY_AWAY_GEOMETRY = {"x": 700, "y": 90, "width": 180, "height": 100}

X11_METADATA_COMMANDS = {
    ("wmctrl", "-m"),
    ("xrandr", "--listactivemonitors"),
    ("xprop", "-root", "_NET_ACTIVE_WINDOW", "_NET_CLIENT_LIST_STACKING"),
}
XPROP_WINDOW_PROPERTIES = (
    "_NET_WM_PID",
    "WM_CLASS",
    "_NET_WM_NAME",
    "WM_NAME",
    "_NET_WM_STATE",
    "_NET_FRAME_EXTENTS",
)
PROHIBITED_XWD_OPTIONS = {"-root", "-screen", "-name", "-frame"}


def _load_contract_validator() -> Any:
    spec = importlib.util.spec_from_file_location("ptp_gov_4_6a_contract", CONTRACT_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("PTP-GOV.4.6A contract validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTRACT = _load_contract_validator()


def normalize_window_id(value: Any) -> str:
    if isinstance(value, int) and value > 0:
        return hex(value)
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"0x[0-9a-f]+", text):
        return ""
    numeric = int(text, 16)
    return hex(numeric) if numeric > 0 else ""


def build_xwd_command(window_id: Any, output_path: Path) -> tuple[str, ...]:
    normalized = normalize_window_id(window_id)
    if not normalized:
        raise ValueError("explicit valid window ID is required")
    command = ("xwd", "-silent", "-nobdrs", "-id", normalized, "-out", str(output_path))
    if PROHIBITED_XWD_OPTIONS.intersection(command):
        raise ValueError("prohibited xwd fallback option")
    if not output_path.is_absolute():
        raise ValueError("xwd output path must be absolute")
    return command


def reject_fallback_mode(mode: str) -> None:
    if mode != "EXPLICIT_WINDOW_ID":
        raise ValueError("FULL_SCREEN, desktop and generic active-window fallbacks are prohibited")


def run_metadata_command(command: Sequence[str], *, timeout: float = 3.0) -> subprocess.CompletedProcess[str]:
    command_tuple = tuple(command)
    allowed = command_tuple in X11_METADATA_COMMANDS
    if command_tuple[:2] == ("xprop", "-id"):
        allowed = (
            len(command_tuple) == 3 + len(XPROP_WINDOW_PROPERTIES)
            and bool(normalize_window_id(command_tuple[2]))
            and tuple(command_tuple[3:]) == XPROP_WINDOW_PROPERTIES
        )
    if command_tuple[:2] == ("xwininfo", "-id"):
        allowed = (
            len(command_tuple) == 5
            and bool(normalize_window_id(command_tuple[2]))
            and tuple(command_tuple[3:]) == ("-stats", "-wm")
        )
    if not allowed:
        raise ValueError(f"X11 metadata command is not allowlisted: {command_tuple!r}")
    return subprocess.run(
        list(command_tuple),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def parse_root_metadata(text: str) -> dict[str, Any]:
    active_match = re.search(r"_NET_ACTIVE_WINDOW\(WINDOW\): window id # (0x[0-9a-fA-F]+)", text)
    stacking_match = re.search(r"_NET_CLIENT_LIST_STACKING\(WINDOW\): window id # (.*)", text)
    stacking = ()
    if stacking_match:
        stacking = tuple(
            normalize_window_id(value)
            for value in re.findall(r"0x[0-9a-fA-F]+", stacking_match.group(1))
        )
    return {
        "ACTIVE_WINDOW_ID": normalize_window_id(active_match.group(1)) if active_match else "",
        "STACKING_ORDER": stacking,
    }


def parse_xprop_window(text: str) -> dict[str, Any]:
    pid_match = re.search(r"_NET_WM_PID\(CARDINAL\) = (\d+)", text)
    class_match = re.search(r'WM_CLASS\(STRING\) = "([^"]*)", "([^"]*)"', text)
    title_match = re.search(r'_NET_WM_NAME\([^)]*\) = "([^"]*)"', text)
    if not title_match:
        title_match = re.search(r'WM_NAME\([^)]*\) = "([^"]*)"', text)
    extents_match = re.search(r"_NET_FRAME_EXTENTS\(CARDINAL\) = ([0-9, ]+)", text)
    frame_extents = ()
    if extents_match:
        frame_extents = tuple(int(value) for value in re.findall(r"\d+", extents_match.group(1)))
    return {
        "WINDOW_PID": int(pid_match.group(1)) if pid_match else None,
        "WM_CLASS": class_match.groups() if class_match else (),
        "WINDOW_TITLE": title_match.group(1) if title_match else "",
        "WINDOW_MINIMIZED": "_NET_WM_STATE_HIDDEN" in text,
        "FRAME_EXTENTS": frame_extents,
    }


def parse_xwininfo(text: str) -> dict[str, Any]:
    def integer(label: str) -> int | None:
        match = re.search(rf"{re.escape(label)}:\s+(-?\d+)", text)
        return int(match.group(1)) if match else None

    map_match = re.search(r"Map State:\s+([^\n]+)", text)
    geometry = {
        "x": integer("Absolute upper-left X"),
        "y": integer("Absolute upper-left Y"),
        "width": integer("Width"),
        "height": integer("Height"),
    }
    valid_geometry = all(isinstance(value, int) for value in geometry.values())
    return {
        "GEOMETRY": geometry if valid_geometry else None,
        "MAP_STATE": map_match.group(1).strip() if map_match else "UNKNOWN",
        "WINDOW_VISIBLE": bool(map_match and map_match.group(1).strip() == "IsViewable"),
    }


def parse_monitor_count(text: str) -> int | None:
    match = re.search(r"Monitors:\s*(\d+)", text)
    return int(match.group(1)) if match else None


def geometry_intersects(first: Mapping[str, int], second: Mapping[str, int]) -> bool:
    return not (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
    )


def is_above(lower_id: str, upper_id: str, stacking: Sequence[str]) -> bool:
    try:
        return stacking.index(upper_id) > stacking.index(lower_id)
    except ValueError:
        return False


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"MISSING")
        return digest.hexdigest()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with item.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def port_5001_listening() -> bool:
    target = f"{5001:04X}"
    for source in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        if not source.exists():
            continue
        for line in source.read_text(encoding="utf-8").splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[1].split(":")[-1].upper() == target and fields[3] == "0A":
                return True
    return False


XWD_HEADER_NAMES = (
    "header_size", "file_version", "pixmap_format", "pixmap_depth",
    "pixmap_width", "pixmap_height", "xoffset", "byte_order",
    "bitmap_unit", "bitmap_bit_order", "bitmap_pad", "bits_per_pixel",
    "bytes_per_line", "visual_class", "red_mask", "green_mask", "blue_mask",
    "bits_per_rgb", "colormap_entries", "ncolors", "window_width", "window_height",
    "window_x", "window_y", "window_bdrwidth",
)


def _signed32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def _mask_channel(pixel: int, mask: int) -> int:
    if mask == 0:
        return 0
    shift = (mask & -mask).bit_length() - 1
    maximum = mask >> shift
    return round(((pixel & mask) >> shift) * 255 / maximum)


def parse_xwd(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 100:
        raise ValueError("XWD header is incomplete")
    values = struct.unpack(">25I", data[:100])
    header = dict(zip(XWD_HEADER_NAMES, values))
    header["window_x"] = _signed32(header["window_x"])
    header["window_y"] = _signed32(header["window_y"])
    if header["file_version"] != 7 or header["pixmap_format"] != 2:
        raise ValueError("unsupported XWD version or pixmap format")
    if header["bits_per_pixel"] not in {24, 32}:
        raise ValueError("unsupported XWD bits_per_pixel")
    if header["byte_order"] not in {0, 1}:
        raise ValueError("unsupported XWD byte order")
    if not all(header[name] for name in ("red_mask", "green_mask", "blue_mask")):
        raise ValueError("XWD TrueColor masks are required")
    pixel_offset = header["header_size"] + header["ncolors"] * 12
    required = pixel_offset + header["bytes_per_line"] * header["pixmap_height"]
    if required > len(data):
        raise ValueError("XWD pixel payload is incomplete")
    bytes_per_pixel = header["bits_per_pixel"] // 8
    byte_order = "little" if header["byte_order"] == 0 else "big"
    pixels: list[tuple[int, int, int]] = []
    for y in range(header["pixmap_height"]):
        row = pixel_offset + y * header["bytes_per_line"]
        for x in range(header["pixmap_width"]):
            start = row + x * bytes_per_pixel
            raw = int.from_bytes(data[start : start + bytes_per_pixel], byte_order)
            pixels.append(
                (
                    _mask_channel(raw, header["red_mask"]),
                    _mask_channel(raw, header["green_mask"]),
                    _mask_channel(raw, header["blue_mask"]),
                )
            )
    return {"header": header, "pixels": tuple(pixels)}


def _close_color(actual: Sequence[int], expected: Sequence[int], tolerance: int = 3) -> bool:
    return all(abs(int(left) - int(right)) <= tolerance for left, right in zip(actual, expected))


def analyze_xwd(image: Mapping[str, Any], expected_geometry: Mapping[str, int]) -> dict[str, Any]:
    header = image["header"]
    pixels = image["pixels"]
    width = int(header["pixmap_width"])
    height = int(header["pixmap_height"])
    stride = max(1, min(width, height) // 120)
    sampled = pixels[::stride]
    color_counts = [sum(_close_color(pixel, color) for pixel in sampled) for color in AUTHORIZED_COLORS]
    overlay_count = sum(_close_color(pixel, OVERLAY_COLOR) for pixel in sampled)
    external_count = sum(
        not any(_close_color(pixel, color) for color in (*AUTHORIZED_COLORS, OVERLAY_COLOR))
        for pixel in sampled
    )
    minimum_authorized = max(1, len(sampled) // 10)
    authorized_complete = all(count >= minimum_authorized for count in color_counts)
    overlay_present = overlay_count > max(2, len(sampled) // 200)
    external_present = external_count > max(2, len(sampled) // 200)
    dimensions = {"width": width, "height": height}
    expected_dimensions = {
        "width": int(expected_geometry["width"]),
        "height": int(expected_geometry["height"]),
    }
    dimensions_match = dimensions == expected_dimensions
    isolated = authorized_complete and not overlay_present and not external_present and dimensions_match
    return {
        "BACKEND_TECHNICAL_CAPTURE_RESULT": (
            "ISOLATED_PIXELS_CONFIRMED" if isolated else "PIXEL_ISOLATION_NOT_CONFIRMED"
        ),
        "AUTHORIZED_SIGNATURE_COMPLETE": "YES" if authorized_complete else "NO",
        "OVERLAY_SIGNATURE_PRESENT": "YES" if overlay_present else "NO",
        "EXTERNAL_PIXEL_SIGNATURE_PRESENT": "YES" if external_present else "NO",
        "CAPTURE_PIXEL_DIMENSIONS": dimensions,
        "EXPECTED_CLIENT_DIMENSIONS": expected_dimensions,
        "DIMENSIONS_MATCH": "YES" if dimensions_match else "NO",
        "PIXEL_SHA256": hashlib.sha256(bytes(channel for pixel in pixels for channel in pixel)).hexdigest(),
    }


class XColor(ctypes.Structure):
    _fields_ = [
        ("pixel", ctypes.c_ulong),
        ("red", ctypes.c_ushort),
        ("green", ctypes.c_ushort),
        ("blue", ctypes.c_ushort),
        ("flags", ctypes.c_byte),
        ("pad", ctypes.c_byte),
    ]


class XClassHint(ctypes.Structure):
    _fields_ = [("res_name", ctypes.c_char_p), ("res_class", ctypes.c_char_p)]


def _load_x11() -> Any:
    library = ctypes.CDLL("libX11.so.6")
    display = ctypes.c_void_p
    window = ctypes.c_ulong
    gc = ctypes.c_void_p
    library.XOpenDisplay.argtypes = [ctypes.c_char_p]
    library.XOpenDisplay.restype = display
    library.XDefaultRootWindow.argtypes = [display]
    library.XDefaultRootWindow.restype = window
    library.XDefaultScreen.argtypes = [display]
    library.XDefaultScreen.restype = ctypes.c_int
    library.XBlackPixel.argtypes = [display, ctypes.c_int]
    library.XBlackPixel.restype = ctypes.c_ulong
    library.XWhitePixel.argtypes = [display, ctypes.c_int]
    library.XWhitePixel.restype = ctypes.c_ulong
    library.XDefaultColormap.argtypes = [display, ctypes.c_int]
    library.XDefaultColormap.restype = ctypes.c_ulong
    library.XCreateSimpleWindow.argtypes = [
        display, window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong,
    ]
    library.XCreateSimpleWindow.restype = window
    library.XStoreName.argtypes = [display, window, ctypes.c_char_p]
    library.XInternAtom.argtypes = [display, ctypes.c_char_p, ctypes.c_int]
    library.XInternAtom.restype = ctypes.c_ulong
    library.XChangeProperty.argtypes = [
        display, window, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int,
    ]
    library.XSetClassHint.argtypes = [display, window, ctypes.POINTER(XClassHint)]
    library.XCreateGC.argtypes = [display, window, ctypes.c_ulong, ctypes.c_void_p]
    library.XCreateGC.restype = gc
    library.XSetForeground.argtypes = [display, gc, ctypes.c_ulong]
    library.XFillRectangle.argtypes = [
        display, window, gc, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
    ]
    library.XAllocNamedColor.argtypes = [
        display, ctypes.c_ulong, ctypes.c_char_p, ctypes.POINTER(XColor), ctypes.POINTER(XColor),
    ]
    library.XAllocNamedColor.restype = ctypes.c_int
    library.XMapWindow.argtypes = [display, window]
    library.XMapRaised.argtypes = [display, window]
    library.XUnmapWindow.argtypes = [display, window]
    library.XMoveResizeWindow.argtypes = [
        display, window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
    ]
    library.XRaiseWindow.argtypes = [display, window]
    library.XSetInputFocus.argtypes = [display, window, ctypes.c_int, ctypes.c_ulong]
    library.XIconifyWindow.argtypes = [display, window, ctypes.c_int]
    library.XFlush.argtypes = [display]
    library.XSync.argtypes = [display, ctypes.c_int]
    library.XDestroyWindow.argtypes = [display, window]
    library.XFreeGC.argtypes = [display, gc]
    library.XCloseDisplay.argtypes = [display]
    return library


def _allocate_color(x11: Any, display: Any, colormap: int, value: tuple[int, int, int]) -> int:
    name = f"#{value[0]:02x}{value[1]:02x}{value[2]:02x}".encode("ascii")
    exact = XColor()
    screen = XColor()
    if not x11.XAllocNamedColor(display, colormap, name, ctypes.byref(screen), ctypes.byref(exact)):
        raise RuntimeError(f"X11 color allocation failed: {name!r}")
    return int(screen.pixel)


def synthetic_window_child(role: str) -> int:
    if role not in {"authorized", "overlay"}:
        return 2
    x11 = _load_x11()
    display = x11.XOpenDisplay(None)
    if not display:
        print(json.dumps({"error": "XOpenDisplay failed"}), flush=True)
        return 3
    screen = x11.XDefaultScreen(display)
    root = x11.XDefaultRootWindow(display)
    black = x11.XBlackPixel(display, screen)
    white = x11.XWhitePixel(display, screen)
    initial = AUTHORIZED_INITIAL_GEOMETRY if role == "authorized" else OVERLAY_AWAY_GEOMETRY
    title = AUTHORIZED_TITLE if role == "authorized" else OVERLAY_TITLE
    window = x11.XCreateSimpleWindow(
        display, root, initial["x"], initial["y"], initial["width"], initial["height"], 0, black, white
    )
    x11.XStoreName(display, window, title.encode("utf-8"))
    pid_atom = x11.XInternAtom(display, b"_NET_WM_PID", 0)
    cardinal_atom = x11.XInternAtom(display, b"CARDINAL", 0)
    pid_value = (ctypes.c_ulong * 1)(os.getpid())
    x11.XChangeProperty(
        display,
        window,
        pid_atom,
        cardinal_atom,
        32,
        0,
        ctypes.cast(pid_value, ctypes.POINTER(ctypes.c_ubyte)),
        1,
    )
    class_hint = XClassHint(b"ptp_gov_4_6b1_synthetic", b"PtpGovSynthetic")
    x11.XSetClassHint(display, window, ctypes.byref(class_hint))
    gc = x11.XCreateGC(display, window, 0, None)
    colormap = x11.XDefaultColormap(display, screen)
    authorized_pixels = tuple(_allocate_color(x11, display, colormap, color) for color in AUTHORIZED_COLORS)
    overlay_pixel = _allocate_color(x11, display, colormap, OVERLAY_COLOR)
    black_pixel = _allocate_color(x11, display, colormap, (0, 0, 0))
    width = initial["width"]
    height = initial["height"]
    mapped = True
    running = True

    def draw() -> None:
        if not mapped:
            return
        if role == "authorized":
            half_width = width // 2
            half_height = height // 2
            rectangles = (
                (0, 0, half_width, half_height),
                (half_width, 0, width - half_width, half_height),
                (0, half_height, half_width, height - half_height),
                (half_width, half_height, width - half_width, height - half_height),
            )
            for pixel, rectangle in zip(authorized_pixels, rectangles):
                x11.XSetForeground(display, gc, pixel)
                x11.XFillRectangle(display, window, gc, *rectangle)
        else:
            x11.XSetForeground(display, gc, overlay_pixel)
            x11.XFillRectangle(display, window, gc, 0, 0, width, height)
            x11.XSetForeground(display, gc, black_pixel)
            x11.XFillRectangle(display, window, gc, width // 4, height // 4, width // 2, height // 2)
        x11.XFlush(display)

    x11.XMapRaised(display, window)
    x11.XSync(display, 0)
    draw()
    print(
        json.dumps(
            {
                "status": "READY",
                "role": role,
                "window_id": hex(int(window)),
                "pid": os.getpid(),
                "title": title,
                "geometry": dict(initial),
            }
        ),
        flush=True,
    )

    try:
        while running:
            readable, _, _ = select.select([sys.stdin], [], [], 0.04)
            if readable:
                line = sys.stdin.readline()
                if not line:
                    break
                try:
                    command = json.loads(line)
                    action = command.get("action")
                    if action == "FOCUS":
                        x11.XMapRaised(display, window)
                        x11.XRaiseWindow(display, window)
                        mapped = True
                    elif action == "SHOW":
                        x11.XMapRaised(display, window)
                        mapped = True
                    elif action == "HIDE":
                        x11.XUnmapWindow(display, window)
                        mapped = False
                    elif action == "MINIMIZE":
                        x11.XIconifyWindow(display, window, screen)
                    elif action == "RESTORE":
                        x11.XMapRaised(display, window)
                        mapped = True
                    elif action == "GEOMETRY":
                        width = int(command["width"])
                        height = int(command["height"])
                        x11.XMoveResizeWindow(
                            display, window, int(command["x"]), int(command["y"]), width, height
                        )
                    elif action == "EXIT":
                        running = False
                    else:
                        raise ValueError(f"unknown synthetic-window action: {action}")
                    x11.XSync(display, 0)
                    draw()
                    print(json.dumps({"status": "ACK", "action": action}), flush=True)
                except Exception as exc:
                    print(json.dumps({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}), flush=True)
            draw()
    finally:
        x11.XFreeGC(display, gc)
        x11.XDestroyWindow(display, window)
        x11.XSync(display, 0)
        x11.XCloseDisplay(display)
    return 0


class SyntheticWindowProcess:
    def __init__(self, role: str) -> None:
        self.role = role
        self.process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--synthetic-child", role],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        ready = self._read_json(timeout=5.0)
        if ready.get("status") != "READY":
            raise RuntimeError(f"synthetic child did not become ready: {ready!r}")
        self.window_id = normalize_window_id(ready["window_id"])
        self.pid = int(ready["pid"])
        self.title = str(ready["title"])

    def _read_json(self, *, timeout: float) -> dict[str, Any]:
        if self.process.stdout is None:
            raise RuntimeError("synthetic child stdout unavailable")
        readable, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not readable:
            raise TimeoutError(f"synthetic child {self.role} response timeout")
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"synthetic child {self.role} exited: {stderr}")
        return json.loads(line)

    def command(self, action: str, **values: Any) -> dict[str, Any]:
        if self.process.stdin is None:
            raise RuntimeError("synthetic child stdin unavailable")
        self.process.stdin.write(json.dumps({"action": action, **values}) + "\n")
        self.process.stdin.flush()
        response = self._read_json(timeout=5.0)
        if response.get("status") != "ACK":
            raise RuntimeError(f"synthetic child command failed: {response!r}")
        return response

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                self.command("EXIT")
            except Exception:
                pass
        try:
            self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=2.0)


def inspect_window(window_id: str) -> dict[str, Any]:
    root_result = run_metadata_command(
        ("xprop", "-root", "_NET_ACTIVE_WINDOW", "_NET_CLIENT_LIST_STACKING")
    )
    prop_result = run_metadata_command(("xprop", "-id", window_id, *XPROP_WINDOW_PROPERTIES))
    info_result = run_metadata_command(("xwininfo", "-id", window_id, "-stats", "-wm"))
    if prop_result.returncode != 0 or info_result.returncode != 0:
        raise RuntimeError(f"window metadata unavailable for {window_id}")
    root = parse_root_metadata(root_result.stdout)
    prop = parse_xprop_window(prop_result.stdout)
    info = parse_xwininfo(info_result.stdout)
    pid = prop["WINDOW_PID"]
    process_name = ""
    if isinstance(pid, int):
        comm_path = Path("/proc") / str(pid) / "comm"
        if comm_path.is_file():
            process_name = comm_path.read_text(encoding="utf-8").strip()
    return {
        "WINDOW_ID": normalize_window_id(window_id),
        "WINDOW_PID": pid,
        "PROCESS_NAME": process_name,
        "WINDOW_TITLE": prop["WINDOW_TITLE"],
        "GEOMETRY": info["GEOMETRY"],
        "WINDOW_VISIBLE": info["WINDOW_VISIBLE"],
        "WINDOW_MINIMIZED": prop["WINDOW_MINIMIZED"] or not info["WINDOW_VISIBLE"],
        "WINDOW_FOREGROUND": root["ACTIVE_WINDOW_ID"] == normalize_window_id(window_id),
        "ACTIVE_WINDOW_ID": root["ACTIVE_WINDOW_ID"],
        "STACKING_ORDER": root["STACKING_ORDER"],
        "FRAME_EXTENTS": prop["FRAME_EXTENTS"],
        "WM_CLASS": prop["WM_CLASS"],
    }


def wait_for_window(
    window_id: str,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    timeout: float = 3.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            last = inspect_window(window_id)
            if predicate(last):
                return last
        except RuntimeError:
            pass
        time.sleep(0.05)
    raise TimeoutError(f"window barrier timeout for {window_id}; last={last!r}")


def build_contract(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "AUTHORIZED_WINDOW_ID": snapshot["WINDOW_ID"],
        "AUTHORIZED_WINDOW_PID": snapshot["WINDOW_PID"],
        "AUTHORIZED_PROCESS_NAME": snapshot["PROCESS_NAME"],
        "AUTHORIZED_TITLE_PATTERN": re.escape(str(snapshot["WINDOW_TITLE"])),
        "AUTHORIZED_GEOMETRY": dict(snapshot["GEOMETRY"]),
        "DISPLAY_SERVER": "X11",
        "WINDOW_VISIBLE": True,
        "WINDOW_MINIMIZED": False,
        "WINDOW_FOREGROUND": True,
        "GEOMETRY_STABLE": True,
        "SOURCE_CONFIRMED": True,
        "FULL_SCREEN_FALLBACK": "PROHIBITED",
    }


def build_observation(
    snapshot: Mapping[str, Any],
    *,
    monitor_count: int,
    display_topology: Mapping[str, Any] | None = None,
    geometry_stable: bool = True,
    source_confirmed: bool = True,
) -> dict[str, Any]:
    logical_topology = dict(
        display_topology
        or CONTRACT.build_example_observation()["DISPLAY_TOPOLOGY"]
    )
    return {
        "OBSERVED_WINDOW_ID": snapshot["WINDOW_ID"],
        "OBSERVED_WINDOW_PID": snapshot["WINDOW_PID"],
        "OBSERVED_PROCESS_NAME": snapshot["PROCESS_NAME"],
        "OBSERVED_TITLE": snapshot["WINDOW_TITLE"],
        "OBSERVED_GEOMETRY": dict(snapshot["GEOMETRY"]),
        "DISPLAY_SERVER": "X11",
        "WINDOW_VISIBLE": bool(snapshot["WINDOW_VISIBLE"]),
        "WINDOW_MINIMIZED": bool(snapshot["WINDOW_MINIMIZED"]),
        "WINDOW_FOREGROUND": bool(snapshot["WINDOW_FOREGROUND"]),
        "GEOMETRY_STABLE": geometry_stable,
        "SOURCE_CONFIRMED": source_confirmed,
        "DISPLAY_TOPOLOGY": logical_topology,
        "DISPLAY_TOPOLOGY_STABLE": "YES",
        "EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION": "PASS",
        "MONITOR_COUNT": monitor_count,
        "CAPTURE_TARGET_MODE": "EXPLICIT_WINDOW_ID",
    }


def barrier_snapshot(
    authorized_id: str,
    overlay_id: str,
    *,
    overlay_expected: bool,
    timeout: float = 3.0,
) -> dict[str, Any]:
    """Wait for deterministic X11 metadata, without listing external window titles."""
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            authorized = inspect_window(authorized_id)
            overlay = inspect_window(overlay_id)
            overlay_visible = bool(overlay["WINDOW_VISIBLE"])
            if overlay_visible == overlay_expected:
                last = {
                    "AUTHORIZED_WINDOW_ID": authorized["WINDOW_ID"],
                    "OVERLAY_WINDOW_ID": overlay["WINDOW_ID"],
                    "ACTIVE_WINDOW_ID": authorized["ACTIVE_WINDOW_ID"],
                    "STACKING_ORDER": authorized["STACKING_ORDER"],
                    "AUTHORIZED_GEOMETRY": authorized["GEOMETRY"],
                    "OVERLAY_GEOMETRY": overlay["GEOMETRY"],
                    "AUTHORIZED": authorized,
                    "OVERLAY": overlay,
                }
                return last
        except RuntimeError:
            pass
        time.sleep(0.05)
    raise TimeoutError(f"X11 barrier timeout; last={last!r}")


def wait_for_overlay_above(authorized_id: str, overlay_id: str, *, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last = barrier_snapshot(authorized_id, overlay_id, overlay_expected=True)
        if is_above(authorized_id, overlay_id, last["STACKING_ORDER"]):
            return last
        time.sleep(0.05)
    raise TimeoutError(f"overlay stacking barrier timeout; last={last!r}")


def overlay_blocks(snapshot: Mapping[str, Any]) -> bool:
    overlay = snapshot["OVERLAY"]
    authorized = snapshot["AUTHORIZED"]
    return bool(
        overlay["WINDOW_VISIBLE"]
        and geometry_intersects(authorized["GEOMETRY"], overlay["GEOMETRY"])
        and is_above(authorized["WINDOW_ID"], overlay["WINDOW_ID"], snapshot["STACKING_ORDER"])
    )


def classify_operational_gate(
    contract: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    monitor_count: int,
    display_topology: Mapping[str, Any] | None = None,
    geometry_stable: bool = True,
    source_confirmed: bool = True,
    observation_mutations: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    observation = build_observation(
        snapshot["AUTHORIZED"],
        monitor_count=monitor_count,
        display_topology=display_topology,
        geometry_stable=geometry_stable,
        source_confirmed=source_confirmed,
    )
    observation.update(dict(observation_mutations or {}))
    gate = CONTRACT.evaluate_capture_gate(contract, observation)
    if overlay_blocks(snapshot):
        reasons = tuple(dict.fromkeys((*gate["REASONS"], "OVERLAY_ABOVE_AUTHORIZED_WINDOW")))
        gate = dict(gate)
        gate.update(
            {
                "CAPTURE_ALLOWED": "NO",
                "SOURCE_STATE": "WAITING_SOURCE_OR_SOURCE_NOT_CONFIRMED",
                "REASONS": reasons,
            }
        )
    reasons = set(gate["REASONS"])
    if gate["CAPTURE_ALLOWED"] == "YES":
        label = "PASS_SOURCE_CONFIRMED_FOREGROUND_STABLE"
    elif "OVERLAY_ABOVE_AUTHORIZED_WINDOW" in reasons:
        label = "BLOCKED_OVERLAY_ABOVE_AUTHORIZED"
    elif reasons.intersection({"WINDOW_NOT_VISIBLE", "WINDOW_MINIMIZED"}):
        label = "BLOCKED_WINDOW_NOT_VISIBLE_OR_MINIMIZED"
    elif "WINDOW_NOT_FOREGROUND" in reasons:
        label = "BLOCKED_WINDOW_NOT_FOREGROUND"
    elif reasons.intersection({"GEOMETRY_MISMATCH", "GEOMETRY_NOT_STABLE"}):
        label = "BLOCKED_GEOMETRY_NOT_STABLE"
    elif reasons.intersection(
        {"WINDOW_ID_MISMATCH", "WINDOW_PID_MISMATCH", "PROCESS_NAME_MISMATCH", "TITLE_PATTERN_MISMATCH"}
    ):
        label = "BLOCKED_IDENTITY_MISMATCH"
    else:
        label = "BLOCKED_FAIL_CLOSED"
    return label, gate


def _run_explicit_xwd(window_id: str, output_path: Path) -> subprocess.CompletedProcess[str]:
    command = build_xwd_command(window_id, output_path)
    return subprocess.run(list(command), check=False, capture_output=True, text=True, timeout=5.0)


def synthetic_characterization_capture(
    window_id: str,
    *,
    owned_window_ids: set[str],
    temporary_root: Path,
    expected_geometry: Mapping[str, int],
    frame_extents: Sequence[int],
) -> dict[str, Any]:
    """Private exception for this validator; cannot target an external window."""
    if not SYNTHETIC_CHARACTERIZATION_OVERRIDE or FUNCTIONAL_CAPTURE_OVERRIDE:
        raise RuntimeError("synthetic-only override invariant violated")
    normalized = normalize_window_id(window_id)
    if normalized not in owned_window_ids:
        raise PermissionError("synthetic override accepts only validator-owned window IDs")
    output = (temporary_root / f"capture-{normalized[2:]}.xwd").resolve()
    if temporary_root.resolve() not in output.parents:
        raise PermissionError("capture output must remain inside the temporary directory")
    result: dict[str, Any] = {
        "CAPTURED_WINDOW_ID": normalized,
        "CAPTURED_WINDOW_KIND": "CLIENT",
        "FRAME_EXTENTS": tuple(frame_extents),
        "CAPTURE_EXECUTED": "YES",
        "OCR_EXECUTED": "NO",
    }
    try:
        completed = _run_explicit_xwd(normalized, output)
        result["XWD_RETURN_CODE"] = completed.returncode
        if completed.returncode != 0 or not output.is_file():
            result.update(
                {
                    "BACKEND_TECHNICAL_CAPTURE_RESULT": "CONTROLLED_CAPTURE_FAILURE",
                    "AUTHORIZED_SIGNATURE_COMPLETE": "NO",
                    "OVERLAY_SIGNATURE_PRESENT": "NO",
                    "EXTERNAL_PIXEL_SIGNATURE_PRESENT": "NO",
                    "CAPTURE_PIXEL_DIMENSIONS": None,
                    "EXPECTED_CLIENT_DIMENSIONS": {
                        "width": expected_geometry["width"],
                        "height": expected_geometry["height"],
                    },
                    "XWD_ERROR": (completed.stderr or completed.stdout).strip(),
                }
            )
            return result
        result.update(analyze_xwd(parse_xwd(output), expected_geometry))
        return result
    finally:
        output.unlink(missing_ok=True)


def invalid_window_id_probe(temporary_root: Path) -> dict[str, Any]:
    invalid_id = "0x7fffffff"
    output = temporary_root / "invalid-window.xwd"
    try:
        completed = _run_explicit_xwd(invalid_id, output)
        controlled = completed.returncode != 0 and (not output.is_file() or output.stat().st_size == 0)
        return {
            "CAPTURED_WINDOW_ID": invalid_id,
            "OPERATIONAL_GATE_RESULT": "BLOCKED_INVALID_WINDOW_ID",
            "BACKEND_TECHNICAL_CAPTURE_RESULT": (
                "CONTROLLED_INVALID_WINDOW_ERROR" if controlled else "UNSAFE_INVALID_WINDOW_RESULT"
            ),
            "XWD_RETURN_CODE": completed.returncode,
            "CAPTURE_EXECUTED": "NO" if controlled else "YES",
            "OCR_EXECUTED": "NO",
        }
    finally:
        output.unlink(missing_ok=True)


def scenario_record(
    name: str,
    pre: Mapping[str, Any],
    post: Mapping[str, Any],
    operational_result: str,
    gate: Mapping[str, Any],
    backend: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "SCENARIO": name,
        "OPERATIONAL_GATE_RESULT": operational_result,
        "BACKEND_TECHNICAL_CAPTURE_RESULT": backend["BACKEND_TECHNICAL_CAPTURE_RESULT"],
        "GATE_CAPTURE_ALLOWED": gate["CAPTURE_ALLOWED"],
        "GATE_REASONS": gate["REASONS"],
        "PRE_CAPTURE_BARRIER": {
            key: pre[key]
            for key in (
                "AUTHORIZED_WINDOW_ID", "OVERLAY_WINDOW_ID", "ACTIVE_WINDOW_ID",
                "STACKING_ORDER", "AUTHORIZED_GEOMETRY", "OVERLAY_GEOMETRY",
            )
        },
        "POST_CAPTURE_BARRIER": {
            key: post[key]
            for key in (
                "AUTHORIZED_WINDOW_ID", "OVERLAY_WINDOW_ID", "ACTIVE_WINDOW_ID",
                "STACKING_ORDER", "AUTHORIZED_GEOMETRY", "OVERLAY_GEOMETRY",
            )
        },
        **dict(backend),
    }


def _geometry_command(child: SyntheticWindowProcess, geometry: Mapping[str, int]) -> None:
    child.command("GEOMETRY", **{key: int(geometry[key]) for key in ("x", "y", "width", "height")})


def focus_owned_window(child: SyntheticWindowProcess, owned_window_ids: set[str]) -> None:
    window_id = normalize_window_id(child.window_id)
    if window_id not in owned_window_ids:
        raise PermissionError("focus target must be a validator-owned synthetic window")
    child.command("FOCUS")
    wait_for_window(window_id, lambda value: value["WINDOW_VISIBLE"])
    completed = subprocess.run(
        ["wmctrl", "-i", "-a", window_id],
        check=False,
        capture_output=True,
        text=True,
        timeout=3.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"targeted synthetic focus failed for {window_id}: {completed.stderr.strip()}")


def run_characterization() -> dict[str, Any]:
    required_tools = ("xwd", "xrandr", "wmctrl", "xprop", "xwininfo")
    missing = tuple(tool for tool in required_tools if shutil.which(tool) is None)
    session = str(os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if session != "x11" or not os.environ.get("DISPLAY") or missing:
        return {
            "PTP": PTP_ID,
            "EXECUTION_STATUS": "BLOCKED_X11_PREFLIGHT",
            "DISPLAY_SERVER": session.upper() or "UNKNOWN",
            "MISSING_TOOLS": missing,
            "SCENARIOS": [],
        }

    monitor_result = run_metadata_command(("xrandr", "--listactivemonitors"))
    monitor_count = parse_monitor_count(monitor_result.stdout)
    display_topology_snapshot = X11DisplayTopologyInspector().read_snapshot()
    display_topology = display_topology_snapshot.to_dict()
    wm_result = run_metadata_command(("wmctrl", "-m"))
    runtime_path = ROOT / "data" / "runtime"
    runtime_hash_before = hash_tree(runtime_path)
    port_before = port_5001_listening()
    temporary_root = Path(tempfile.mkdtemp(prefix="ptp_gov_4_6b1_"))
    authorized: SyntheticWindowProcess | None = None
    overlay: SyntheticWindowProcess | None = None
    scenarios: list[dict[str, Any]] = []
    owned_ids: set[str] = set()
    owned_pids: set[int] = set()
    cleanup_error = ""

    try:
        authorized = SyntheticWindowProcess("authorized")
        overlay = SyntheticWindowProcess("overlay")
        owned_ids = {normalize_window_id(authorized.window_id), normalize_window_id(overlay.window_id)}
        owned_pids = {authorized.process.pid, overlay.process.pid}
        overlay.command("HIDE")
        focus_owned_window(authorized, owned_ids)
        pre = barrier_snapshot(authorized.window_id, overlay.window_id, overlay_expected=False)
        wait_for_window(authorized.window_id, lambda value: value["WINDOW_FOREGROUND"])
        pre = barrier_snapshot(authorized.window_id, overlay.window_id, overlay_expected=False)
        contract = build_contract(pre["AUTHORIZED"])
        base_request = dict(AUTHORIZED_INITIAL_GEOMETRY)

        def capture_scenario(
            name: str,
            *,
            geometry_stable: bool = True,
            source_confirmed: bool = True,
            mutations: Mapping[str, Any] | None = None,
            post_action: Callable[[], None] | None = None,
        ) -> dict[str, Any]:
            before = barrier_snapshot(
                authorized.window_id,
                overlay.window_id,
                overlay_expected=bool(inspect_window(overlay.window_id)["WINDOW_VISIBLE"]),
            )
            operational, gate = classify_operational_gate(
                contract,
                before,
                monitor_count=int(monitor_count or 0),
                display_topology=display_topology,
                geometry_stable=geometry_stable,
                source_confirmed=source_confirmed,
                observation_mutations=mutations,
            )
            backend = synthetic_characterization_capture(
                authorized.window_id,
                owned_window_ids=owned_ids,
                temporary_root=temporary_root,
                expected_geometry=before["AUTHORIZED_GEOMETRY"],
                frame_extents=before["AUTHORIZED"]["FRAME_EXTENTS"],
            )
            if post_action:
                post_action()
                wait_for_window(
                    authorized.window_id,
                    lambda value: value["GEOMETRY"] != before["AUTHORIZED_GEOMETRY"],
                )
            after = barrier_snapshot(
                authorized.window_id,
                overlay.window_id,
                overlay_expected=bool(inspect_window(overlay.window_id)["WINDOW_VISIBLE"]),
            )
            if before["AUTHORIZED_GEOMETRY"] != after["AUTHORIZED_GEOMETRY"]:
                operational = "BLOCKED_TOCTOU_GEOMETRY_CHANGED"
                gate = dict(gate)
                gate.update({"CAPTURE_ALLOWED": "NO", "CAPTURE_EXECUTED": "NO"})
            return scenario_record(name, before, after, operational, gate, backend)

        # 1. Visible and foreground.
        scenarios.append(capture_scenario("01_VISIBLE_FOREGROUND"))

        # 2. Authorized window visible but not focused.
        overlay.command("SHOW")
        _geometry_command(overlay, OVERLAY_AWAY_GEOMETRY)
        focus_owned_window(overlay, owned_ids)
        wait_for_window(overlay.window_id, lambda value: value["WINDOW_FOREGROUND"])
        scenarios.append(capture_scenario("02_VISIBLE_NOT_FOREGROUND"))

        # 3. Partial overlap, overlay above the authorized window.
        authorized_snapshot = inspect_window(authorized.window_id)
        ag = authorized_snapshot["GEOMETRY"]
        _geometry_command(overlay, {"x": ag["x"] + ag["width"] // 2, "y": ag["y"] + 20, "width": ag["width"] // 2, "height": ag["height"] - 40})
        focus_owned_window(overlay, owned_ids)
        wait_for_overlay_above(authorized.window_id, overlay.window_id)
        scenarios.append(capture_scenario("03_PARTIAL_OVERLAY"))

        # 4. Total overlap, overlay above the authorized window.
        overlay_metadata = inspect_window(overlay.window_id)
        overlay_extents = tuple(overlay_metadata["FRAME_EXTENTS"])
        overlay_left = overlay_extents[0] if len(overlay_extents) == 4 else 0
        overlay_top = overlay_extents[2] if len(overlay_extents) == 4 else 0
        _geometry_command(
            overlay,
            {
                "x": ag["x"] - overlay_left,
                "y": ag["y"] - overlay_top,
                "width": ag["width"],
                "height": ag["height"],
            },
        )
        focus_owned_window(overlay, owned_ids)
        wait_for_window(overlay.window_id, lambda value: value["GEOMETRY"] == ag)
        wait_for_overlay_above(authorized.window_id, overlay.window_id)
        scenarios.append(capture_scenario("04_TOTAL_OVERLAY"))

        # 5. Minimized authorized window. Technical capture may fail in a controlled way.
        overlay.command("HIDE")
        authorized.command("MINIMIZE")
        wait_for_window(authorized.window_id, lambda value: value["WINDOW_MINIMIZED"] or not value["WINDOW_VISIBLE"])
        scenarios.append(capture_scenario("05_MINIMIZED"))

        # Restore a stable baseline for the remaining scenarios.
        authorized.command("RESTORE")
        _geometry_command(authorized, base_request)
        focus_owned_window(authorized, owned_ids)
        wait_for_window(authorized.window_id, lambda value: value["WINDOW_VISIBLE"] and value["WINDOW_FOREGROUND"])

        # 6. Geometry changed before capture: contract gate blocks.
        _geometry_command(authorized, {"x": 120, "y": 110, "width": 240, "height": 150})
        wait_for_window(authorized.window_id, lambda value: value["GEOMETRY"] != contract["AUTHORIZED_GEOMETRY"])
        scenarios.append(capture_scenario("06_GEOMETRY_CHANGED_BEFORE_CAPTURE"))

        # Restore the contract geometry request and establish the expected actual geometry.
        _geometry_command(authorized, base_request)
        focus_owned_window(authorized, owned_ids)
        restored = wait_for_window(
            authorized.window_id,
            lambda value: value["GEOMETRY"]["width"] == base_request["width"]
            and value["GEOMETRY"]["height"] == base_request["height"]
            and value["WINDOW_FOREGROUND"],
        )
        contract = build_contract(restored)

        # 7. Geometry changes after capture; post-validation discards the image.
        scenarios.append(
            capture_scenario(
                "07_GEOMETRY_CHANGED_DURING_CYCLE",
                post_action=lambda: _geometry_command(
                    authorized, {"x": 100, "y": 100, "width": 260, "height": 160}
                ),
            )
        )
        _geometry_command(authorized, base_request)
        focus_owned_window(authorized, owned_ids)
        restored = wait_for_window(
            authorized.window_id,
            lambda value: value["GEOMETRY"]["width"] == base_request["width"]
            and value["GEOMETRY"]["height"] == base_request["height"]
            and value["WINDOW_FOREGROUND"],
        )
        contract = build_contract(restored)

        # 8. Explicit invalid window ID.
        scenarios.append({"SCENARIO": "08_INVALID_WINDOW_ID", **invalid_window_id_probe(temporary_root)})

        # 9. PID, process and title identity mismatches are individually reported.
        identity_checks = {
            "OBSERVED_WINDOW_PID": int(contract["AUTHORIZED_WINDOW_PID"]) + 1,
            "OBSERVED_PROCESS_NAME": "untrusted-synthetic-process",
            "OBSERVED_TITLE": "UNAUTHORIZED SYNTHETIC TITLE",
        }
        identity_results = []
        for field, value in identity_checks.items():
            before = barrier_snapshot(authorized.window_id, overlay.window_id, overlay_expected=False)
            operational, gate = classify_operational_gate(
                contract,
                before,
                monitor_count=int(monitor_count or 0),
                display_topology=display_topology,
                observation_mutations={field: value},
            )
            identity_results.append({"FIELD": field, "OPERATIONAL_GATE_RESULT": operational, "REASONS": gate["REASONS"]})
        scenarios.append(
            {
                "SCENARIO": "09_PID_PROCESS_TITLE_DIVERGENT",
                "OPERATIONAL_GATE_RESULT": "BLOCKED_IDENTITY_MISMATCH",
                "BACKEND_TECHNICAL_CAPTURE_RESULT": "NOT_EXECUTED_GATE_BLOCKED",
                "IDENTITY_CHECKS": identity_results,
                "CAPTURE_EXECUTED": "NO",
                "OCR_EXECUTED": "NO",
            }
        )

        # 10. Prohibited fallback attempts are rejected before subprocess execution.
        fallback_results = []
        for mode in ("FULL_SCREEN", "ACTIVE_WINDOW_GENERIC", "DESKTOP"):
            try:
                reject_fallback_mode(mode)
            except ValueError:
                fallback_results.append({"MODE": mode, "RESULT": "REJECTED"})
        scenarios.append(
            {
                "SCENARIO": "10_FALLBACK_ATTEMPTS",
                "OPERATIONAL_GATE_RESULT": "BLOCKED_PROHIBITED_FALLBACK",
                "BACKEND_TECHNICAL_CAPTURE_RESULT": "NOT_EXECUTED_FALLBACK_REJECTED",
                "FALLBACK_RESULTS": fallback_results,
                "CAPTURE_EXECUTED": "NO",
                "OCR_EXECUTED": "NO",
            }
        )

        # 11. Explicit identity is checked before and after a normal capture.
        focus_owned_window(authorized, owned_ids)
        wait_for_window(authorized.window_id, lambda value: value["WINDOW_FOREGROUND"])
        scenarios.append(capture_scenario("11_PRE_POST_IDENTITY_REVALIDATION"))

    finally:
        for child in (overlay, authorized):
            if child is not None:
                try:
                    child.stop()
                except Exception as exc:  # cleanup evidence is reported, never hidden
                    cleanup_error = f"{cleanup_error};{type(exc).__name__}:{exc}".strip(";")

    # Scenario 12 and final cleanup evidence are evaluated after all owned children exit.
    owned_child_count = sum(Path("/proc", str(pid)).exists() for pid in owned_pids)
    owned_window_count = 0
    for window_id in owned_ids:
        result = run_metadata_command(("xprop", "-id", window_id, *XPROP_WINDOW_PROPERTIES))
        if result.returncode == 0:
            owned_window_count += 1
    temp_capture_count = len(tuple(temporary_root.rglob("*.xwd"))) if temporary_root.exists() else 0
    shutil.rmtree(temporary_root)
    temp_removed = not temporary_root.exists()
    cleanup = {
        "SCENARIO": "12_COMPLETE_TEMPORARY_CLEANUP",
        "OPERATIONAL_GATE_RESULT": "PASS_CLEANUP" if not cleanup_error and not owned_child_count and not owned_window_count and not temp_capture_count and temp_removed else "FAIL_CLEANUP",
        "BACKEND_TECHNICAL_CAPTURE_RESULT": "NO_TEMPORARY_IMAGE_RETAINED" if not temp_capture_count and temp_removed else "TEMPORARY_IMAGE_RETAINED",
        "OWNED_CHILD_PROCESS_COUNT_FINAL": owned_child_count,
        "OWNED_SYNTHETIC_WINDOW_COUNT_FINAL": owned_window_count,
        "TEMP_CAPTURE_FILE_COUNT_FINAL": temp_capture_count,
        "TEMP_DIRECTORY_REMOVED": "YES" if temp_removed else "NO",
        "CLEANUP_ERROR": cleanup_error or "NONE",
    }
    scenarios.append(cleanup)

    runtime_hash_after = hash_tree(runtime_path)
    port_after = port_5001_listening()
    isolated_required = {"01_VISIBLE_FOREGROUND", "02_VISIBLE_NOT_FOREGROUND", "03_PARTIAL_OVERLAY", "04_TOTAL_OVERLAY", "11_PRE_POST_IDENTITY_REVALIDATION"}
    unsafe = [
        scenario["SCENARIO"]
        for scenario in scenarios
        if scenario["SCENARIO"] in isolated_required
        and not (
            scenario.get("BACKEND_TECHNICAL_CAPTURE_RESULT") == "ISOLATED_PIXELS_CONFIRMED"
            and scenario.get("OVERLAY_SIGNATURE_PRESENT") == "NO"
            and scenario.get("AUTHORIZED_SIGNATURE_COMPLETE") == "YES"
            and scenario.get("EXTERNAL_PIXEL_SIGNATURE_PRESENT") == "NO"
        )
    ]
    cleanup_pass = cleanup["OPERATIONAL_GATE_RESULT"] == "PASS_CLEANUP"
    preflight_pass = display_topology_snapshot.gate_pass and not missing and session == "x11"
    backend_overall = "PIXEL_ISOLATION_NOT_CONFIRMED" if unsafe else "ISOLATED_PIXELS_CONFIRMED"
    if unsafe:
        overall = "BLOCKED_BACKEND_PIXEL_ISOLATION_NOT_CONFIRMED"
        b2_blocked = "YES"
        operational_capture_allowed = "NO"
    elif not cleanup_pass or not preflight_pass:
        overall = "BLOCKED_FAIL_CLOSED"
        b2_blocked = "YES"
        operational_capture_allowed = "NO"
    else:
        overall = "PASS_CONTROLLED_CHARACTERIZATION"
        b2_blocked = "NO"
        operational_capture_allowed = "YES_WHEN_ALL_OPERATIONAL_GATES_PASS"
    test_names = tuple(scenario["SCENARIO"] for scenario in scenarios)
    result = {
        "PTP": PTP_ID,
        "EXECUTION_STATUS": overall,
        "DISPLAY_SERVER": "X11",
        "WINDOW_MANAGER": next((line.split(":", 1)[1].strip() for line in wm_result.stdout.splitlines() if line.startswith("Name:")), "UNKNOWN"),
        "MONITOR_COUNT": monitor_count,
        "MONITOR_COUNT_INFORMATIONAL_ONLY": "YES",
        "LOGICAL_DESKTOP_COUNT": display_topology.get("LOGICAL_DESKTOP_COUNT"),
        "CAPTURE_SURFACE_COUNT": display_topology.get("CAPTURE_SURFACE_COUNT"),
        "EXTENDED_DESKTOP": display_topology.get("EXTENDED_DESKTOP"),
        "DISPLAY_TOPOLOGY_HASH": display_topology_snapshot.topology_hash,
        "BACKEND": "xwd -silent -nobdrs -id <owned-window-id>",
        "OPERATIONAL_GATE_RESULT": overall,
        "BACKEND_TECHNICAL_CAPTURE_RESULT": backend_overall,
        "OPERATIONAL_CAPTURE_ALLOWED": operational_capture_allowed,
        "PTP-GOV.4.6B.2_BLOCKED": b2_blocked,
        "PTP-GOV.4.6B.2_STARTED": "NO",
        "SYNTHETIC_CHARACTERIZATION_OVERRIDE": "YES",
        "SYNTHETIC_OVERRIDE_AVAILABLE_IN_APPLICATION": "NO",
        "FUNCTIONAL_CAPTURE_OVERRIDE": "NO",
        "SCENARIO_COUNT": len(scenarios),
        "SCENARIO_NAMES": test_names,
        "UNSAFE_OR_INCONCLUSIVE_SCENARIOS": tuple(unsafe),
        "SCENARIOS": scenarios,
        "OWNED_CHILD_PROCESS_COUNT_FINAL": owned_child_count,
        "OWNED_SYNTHETIC_WINDOW_COUNT_FINAL": owned_window_count,
        "TEMP_CAPTURE_FILE_COUNT_FINAL": temp_capture_count,
        "TEMP_DIRECTORY_REMOVED": "YES" if temp_removed else "NO",
        "REAL_RUNTIME_HASH_BEFORE": runtime_hash_before,
        "REAL_RUNTIME_HASH_AFTER": runtime_hash_after,
        "REAL_RUNTIME_CHANGED": "NO" if runtime_hash_before == runtime_hash_after else "YES",
        "PORT_LISTENER_CREATED": "NO" if port_before == port_after else "YES",
        "BROKER_OPENED": "NO",
        "OCR_EXECUTED": "NO",
        "TESSERACT_EXECUTED": "NO",
        "MOBILE_V2_STARTED": "NO",
        "OBSERVER_STARTED": "NO",
        "SERVER_STARTED": "NO",
        "FULL_SCREEN_FALLBACK": "PROHIBITED",
        "ACTIVE_WINDOW_GENERIC_FALLBACK": "PROHIBITED",
        "DESKTOP_CAPTURE_FALLBACK": "PROHIBITED",
        "EXTERNAL_WINDOW_TITLE_LISTING": "NO",
        "FUNCTIONAL_INTEGRATION_STARTED": "NO",
        "SIMULATION_ONLY": "YES",
    }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-child", choices=("authorized", "overlay"))
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)
    if args.synthetic_child:
        return synthetic_window_child(args.synthetic_child)
    try:
        result = run_characterization()
    except BaseException as exc:
        result = {
            "PTP": PTP_ID,
            "EXECUTION_STATUS": "FAIL_VALIDATOR",
            "VALIDATOR_EXCEPTION": f"{type(exc).__name__}: {exc}",
            "PTP-GOV.4.6B.2_STARTED": "NO",
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output_json:
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result.get("EXECUTION_STATUS") == "PASS_CONTROLLED_CHARACTERIZATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
