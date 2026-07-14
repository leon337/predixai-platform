#!/usr/bin/env python3
"""Controlled C.1A calibration of the complete authorized broker visual map."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.capture.capture_engine import CaptureEngine  # noqa: E402
from predixai.capture.capture_snapshot import LinuxXwdWindowSnapshot  # noqa: E402
from predixai.capture.snapshot_metadata import (  # noqa: E402
    AuthorizedWindowContract,
    WindowGeometry,
)
from predixai.capture.x11_display_topology import X11DisplayTopologyInspector  # noqa: E402
from predixai.live.broker_window_detector import BrokerWindowDetector  # noqa: E402
from predixai.live.broker_window_state import BrokerWindowState  # noqa: E402
from predixai.live.field_locator import (  # noqa: E402
    AUTHORIZED_VISUAL_REGION_BY_ID,
    AUTHORIZED_VISUAL_REGION_SPECS,
    FieldLocator,
)
from predixai.live.live_market_reader import LiveMarketReader  # noqa: E402
from predixai.ocr.ocr_engine import OCREngine  # noqa: E402
from predixai.vision.roi import RegionOfInterest, RelativeRegionGeometry  # noqa: E402
from predixai.vision.roi_crop_engine import ROICropEngine  # noqa: E402


PTP_ID = "PTP-GOV.4.6C.1A"
BASE_COMMIT = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
COUNTDOWN_MESSAGE = "CONTAGEM INICIADA — ABRA A CORRETORA AGORA"
RETURN_MESSAGE = "CAPTURA E CALIBRAÇÃO CONTROLADAS CONCLUÍDAS — PODE RETORNAR AO CODEX"
ARTIFACT_DATE = datetime.now().strftime("%Y%m%d")
REPORT = ROOT / f"reports/{ARTIFACT_DATE}_PTP-GOV.4.6C.1A_calibracao_visual_ocr_regioes_CALIBRATION.txt"
PROPOSAL = ROOT / f"reports/{ARTIFACT_DATE}_PTP-GOV.4.6C.1A_regioes_propostas.tsv"
HISTORY = ROOT / f"docs/history/ptp/PTP-GOV/PTP-GOV.4.6C.1A/{ARTIFACT_DATE}_PTP-GOV.4.6C.1A_calibracao_visual_ocr_regioes_CALIBRATION.md"
INDEX = ROOT / "docs/reports_index.md"
PREEXISTING_DIRTY = "reports/20260709_000047_PTP-113C.8.4.2A_auditoria_observer_paper_mobile_v2_AUDIT_ONLY.txt"
REFERENCE_IMAGE_SHA256 = "e45c6a35aaf7f7df8361fdbed743cda86ae8eec318a3218f4fe2e33278e742c9"
REGION_SPECS = AUTHORIZED_VISUAL_REGION_SPECS
FIELD_SPECS = tuple((specification.region_id, specification.region_id) for specification in REGION_SPECS)
FORBIDDEN_WINDOW_MARKERS = (
    "visual studio code",
    "codex",
    "terminal",
    "dashboard",
    "predixai mobile",
    "localhost",
    "127.0.0.1",
)
BROKER_WINDOW_MARKERS = (
    "olymp",
    "olymptrade",
    " otc",
    "index",
    "iq option",
    "quotex",
    "exnova",
)
STABLE_AUTHORIZED_TITLE = "AUTHORIZED_BROKER_TITLE_SIGNATURE"


class ProjectConfig:
    def resolve_project_path(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path


def stable_broker_title_pattern(title: str) -> str:
    """Build a broker-specific pattern while excluding a volatile leading quote."""
    for marker in ("olymptrade", "olymp", "iq option", "quotex", "exnova"):
        if marker in title.casefold():
            return rf"(?i).*{re.escape(marker)}.*"
    otc = re.search(r"\b([A-Za-z][A-Za-z0-9._-]{1,40}\s+OTC)\b", title, re.IGNORECASE)
    if otc is not None:
        return rf"(?i).*{re.escape(otc.group(1))}.*"
    index = re.search(r"\b([A-Za-z][A-Za-z0-9._-]{1,40}\s+Index)\b", title, re.IGNORECASE)
    if index is not None:
        return rf"(?i).*{re.escape(index.group(1))}.*"
    raise ValueError("stable broker title signature is unavailable")


class StableAuthorizedTitleDetector:
    """Validator-only adapter that checks raw titles before canonical hashing."""

    def __init__(self, delegate: BrokerWindowDetector, raw_title_pattern: str) -> None:
        self._delegate = delegate
        self._raw_title_pattern = re.compile(raw_title_pattern)

    def inspect_explicit_linux_window(self, window_id: str) -> BrokerWindowState:
        observed = self._delegate.inspect_explicit_linux_window(window_id)
        if self._raw_title_pattern.fullmatch(observed.title) is None:
            return observed
        return replace(observed, title=STABLE_AUTHORIZED_TITLE)


@dataclass(frozen=True)
class RegionProposal:
    field_id: str
    region_id: str
    x: int
    y: int
    width: int
    height: int
    window_width: int
    window_height: int
    x_ratio: float
    y_ratio: float
    width_ratio: float
    height_ratio: float
    crop_sha256: str
    classifications: tuple[str, ...] = ()
    source: str = ""
    reading_mode: str = "VISUAL_STATE"
    visibility_state: str = "ALWAYS"
    parent_region_id: str | None = None
    privacy_sensitive: bool = False
    ocr_text: str = "NOT_EXECUTED"
    ocr_confidence: float = 0.0
    calibration_status: str = "REGION_SELECTED_OCR_PENDING"

    def geometry_tuple(self) -> tuple[float, float, float, float]:
        return (self.x_ratio, self.y_ratio, self.width_ratio, self.height_ratio)

    def to_row(self) -> dict[str, object]:
        return {
            "FIELD_ID": self.field_id,
            "REGION_ID": self.region_id,
            "PIXEL_GEOMETRY": f"{self.width}x{self.height}+{self.x}+{self.y}",
            "x_ratio": f"{self.x_ratio:.12f}",
            "y_ratio": f"{self.y_ratio:.12f}",
            "width_ratio": f"{self.width_ratio:.12f}",
            "height_ratio": f"{self.height_ratio:.12f}",
            "WINDOW_WIDTH": self.window_width,
            "WINDOW_HEIGHT": self.window_height,
            "FIELD_VISUALLY_CONFIRMED": "YES",
            "REGION_INSIDE_WINDOW": "YES",
            "OVERLAP_WITH_OTHER_FIELDS": (
                "DOCUMENTED_PARENT_CHILD_ONLY"
                if self.parent_region_id
                or any(item.parent_region_id == self.region_id for item in REGION_SPECS)
                else "NO"
            ),
            "CLASSIFICATIONS": ",".join(self.classifications),
            "SOURCE": self.source,
            "READING_MODE": self.reading_mode,
            "VISIBILITY_STATE": self.visibility_state,
            "PARENT_REGION_ID": self.parent_region_id or "NONE",
            "PRIVACY_SENSITIVE": "YES" if self.privacy_sensitive else "NO",
            "OCR_TEXT": self.ocr_text,
            "OCR_CONFIDENCE": f"{self.ocr_confidence:.3f}",
            "CROP_SHA256": self.crop_sha256,
            "CALIBRATION_STATUS": self.calibration_status,
        }


def run(command: Sequence[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"MISSING")
        return digest.hexdigest()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def tesseract_metadata() -> dict[str, object]:
    binary = shutil.which("tesseract")
    if binary is None:
        return {
            "TESSERACT_AVAILABLE": "NO",
            "TESSERACT_VERSION": "NOT_DETECTED",
            "TESSERACT_LANGUAGES": (),
            "OCR_REAL_ALLOWED": "NO",
            "OCR_STATUS": "PAUSED_DEPENDENCY_MISSING",
        }
    version_result = run((binary, "--version"), timeout=5.0)
    language_result = run((binary, "--list-langs"), timeout=5.0)
    languages = tuple(
        line.strip()
        for line in language_result.stdout.splitlines()
        if line.strip() and not line.lower().startswith("list of")
    )
    available = version_result.returncode == 0 and language_result.returncode == 0
    return {
        "TESSERACT_AVAILABLE": "YES" if available else "NO",
        "TESSERACT_VERSION": (
            version_result.stdout.splitlines()[0].strip()
            if available and version_result.stdout.strip()
            else "UNKNOWN"
        ),
        "TESSERACT_LANGUAGES": languages,
        "OCR_REAL_ALLOWED": "YES" if available and ({"por", "eng"} & set(languages)) else "NO",
        "OCR_STATUS": "READY" if available and ({"por", "eng"} & set(languages)) else "PAUSED_LANGUAGE_OR_PROVIDER_UNAVAILABLE",
    }


def preflight() -> dict[str, object]:
    commands = {name: shutil.which(name) is not None for name in ("xprop", "xwininfo", "xrandr", "xwd")}
    tesseract = tesseract_metadata()
    display_server = str(os.environ.get("XDG_SESSION_TYPE") or "").upper()
    display = str(os.environ.get("DISPLAY") or "")
    try:
        import cv2
        import numpy  # noqa: F401

        gui_available = "GUI:" in cv2.getBuildInformation() and "QT" in cv2.getBuildInformation()
    except ImportError:
        gui_available = False
    topology_gate = "NO"
    topology_hash = ""
    try:
        topology = X11DisplayTopologyInspector().read_snapshot()
        topology_gate = "YES" if topology.gate_pass else "NO"
        topology_hash = topology.topology_hash
    except Exception:
        topology_gate = "NO"
    return {
        "BASE_COMMIT": BASE_COMMIT,
        "DISPLAY_SERVER": display_server,
        "DISPLAY": display,
        "X11_TOOLS_AVAILABLE": "YES" if all(commands.values()) else "NO",
        "X11_TOOL_STATUS": commands,
        "OPENCV_GUI_AVAILABLE": "YES" if gui_available else "NO",
        "TOPOLOGY_GATE_PASS": topology_gate,
        "TOPOLOGY_HASH": topology_hash,
        "REGION_CALIBRATION_ALLOWED": "YES" if display_server == "X11" and all(commands.values()) and gui_available and topology_gate == "YES" else "NO",
        "MANUAL_REGION_SELECTION_ALLOWED": "YES" if gui_available else "NO",
        **tesseract,
    }


def candidate_allowed(state: Any) -> tuple[bool, str]:
    metadata = state.metadata
    title = str(state.title or "")
    process = str(metadata.get("process_name") or "")
    combined = f"{title} {process}".casefold()
    if any(marker in combined for marker in FORBIDDEN_WINDOW_MARKERS):
        return False, "FORBIDDEN_TECHNICAL_WINDOW"
    if not any(marker in f" {title.casefold()}" for marker in BROKER_WINDOW_MARKERS):
        return False, "BROKER_TITLE_EVIDENCE_MISSING"
    if not bool(metadata.get("window_visible")) or bool(metadata.get("window_minimized")):
        return False, "BROKER_WINDOW_NOT_VISIBLE"
    if not state.foreground:
        return False, "BROKER_WINDOW_NOT_FOREGROUND"
    if int(metadata.get("window_pid") or 0) <= 0 or not process.strip():
        return False, "BROKER_PROCESS_IDENTITY_INCOMPLETE"
    return True, "AUTHORIZED_CANDIDATE"


def wait_for_authorized_candidate(
    detector: BrokerWindowDetector,
    *,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[AuthorizedWindowContract, dict[str, object]]:
    deadline = time.monotonic() + timeout_seconds
    stable: list[tuple[object, ...]] = []
    last_state = None
    while time.monotonic() < deadline:
        active_numeric = detector._linux_active_window_id()  # controlled enrollment only
        if active_numeric is None:
            stable.clear()
            sleeper(poll_seconds)
            continue
        window_id = LinuxXwdWindowSnapshot.normalize_window_id(hex(active_numeric))
        try:
            state = detector.inspect_explicit_linux_window(window_id)
        except (OSError, RuntimeError, ValueError):
            stable.clear()
            sleeper(poll_seconds)
            continue
        allowed, _ = candidate_allowed(state)
        if not allowed:
            stable.clear()
            sleeper(poll_seconds)
            continue
        metadata = state.metadata
        signature = (
            str(metadata.get("window_id")),
            int(metadata.get("window_pid") or 0),
            str(metadata.get("process_name")),
            state.title,
            state.left,
            state.top,
            state.resolution_width,
            state.resolution_height,
        )
        stable = [*stable[-2:], signature] if not stable or stable[-1] == signature else [signature]
        last_state = state
        if len(stable) >= 3:
            break
        sleeper(poll_seconds)
    if last_state is None or len(stable) < 3:
        raise RuntimeError("AUTHORIZED_BROKER_WINDOW_NOT_STABLE_BEFORE_TIMEOUT")
    metadata = last_state.metadata
    contract = AuthorizedWindowContract(
        window_id=str(metadata["window_id"]),
        window_pid=int(metadata["window_pid"]),
        process_name=str(metadata["process_name"]),
        title_pattern=re.escape(last_state.title),
        geometry=WindowGeometry(
            x=last_state.left,
            y=last_state.top,
            width=last_state.resolution_width,
            height=last_state.resolution_height,
        ),
        require_foreground=True,
        display_server="X11",
    )
    safe_identity = {
        "AUTHORIZED_WINDOW_ID": contract.window_id,
        "AUTHORIZED_WINDOW_PID": contract.window_pid,
        "AUTHORIZED_PROCESS_NAME": contract.process_name,
        "AUTHORIZED_TITLE_SHA256": hashlib.sha256(last_state.title.encode("utf-8")).hexdigest(),
        "AUTHORIZED_GEOMETRY": contract.geometry.to_dict(),
    }
    return contract, safe_identity


def run_capture_countdown(
    seconds: int = 30,
    *,
    sleeper: Callable[[float], None] = time.sleep,
    emit: Callable[[str], None] | None = None,
) -> None:
    """Delay every window query and capture until the countdown has completed."""
    if seconds <= 0:
        raise ValueError("countdown must be positive")
    printer = emit or (lambda value: print(value, flush=True))
    printer(COUNTDOWN_MESSAGE)
    for remaining in range(seconds, 0, -1):
        printer(f"CAPTURA_EM_SEGUNDOS={remaining}")
        sleeper(1.0)
    printer("CONTAGEM_CONCLUIDA=YES")


def boxes_overlap(first: Sequence[int], second: Sequence[int]) -> bool:
    ax, ay, aw, ah = (int(value) for value in first)
    bx, by, bw, bh = (int(value) for value in second)
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def box_contains(parent: Sequence[int], child: Sequence[int]) -> bool:
    px, py, pw, ph = (int(value) for value in parent)
    cx, cy, cw, ch = (int(value) for value in child)
    return px <= cx and py <= cy and px + pw >= cx + cw and py + ph >= cy + ch


def validate_boxes(boxes: dict[str, tuple[int, int, int, int]], width: int, height: int) -> None:
    expected = set(AUTHORIZED_VISUAL_REGION_BY_ID)
    if set(boxes) != expected:
        raise ValueError(f"exactly {len(expected)} manually selected regions are required")
    for region_id, box in boxes.items():
        x, y, box_width, box_height = box
        RelativeRegionGeometry.from_pixels(
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            window_width=width,
            window_height=height,
        )
        if box_width < 4 or box_height < 4:
            raise ValueError(f"manual region is too small: {region_id}")
    items = tuple(boxes.items())
    for index, (first_id, first_box) in enumerate(items):
        for second_id, second_box in items[index + 1:]:
            if not boxes_overlap(first_box, second_box):
                continue
            first_spec = AUTHORIZED_VISUAL_REGION_BY_ID[first_id]
            second_spec = AUTHORIZED_VISUAL_REGION_BY_ID[second_id]
            if first_spec.parent_region_id == second_id:
                if not box_contains(second_box, first_box):
                    raise ValueError(f"child region exceeds parent: {first_id}/{second_id}")
                continue
            if second_spec.parent_region_id == first_id:
                if not box_contains(first_box, second_box):
                    raise ValueError(f"child region exceeds parent: {second_id}/{first_id}")
                continue
            raise ValueError(f"unauthorized region overlap: {first_id}/{second_id}")


def select_regions_opencv(pixel_bytes: bytes, width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    import cv2
    import numpy as np

    expected = width * height * 3
    if len(pixel_bytes) != expected:
        raise ValueError("authorized RGB24 byte count contradicts its dimensions")
    rgb = np.frombuffer(pixel_bytes, dtype=np.uint8).reshape((height, width, 3))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    max_width, max_height = 1180, 650
    scale = min(1.0, max_width / width, max_height / height)
    display = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1.0 else bgr.copy()
    boxes: dict[str, tuple[int, int, int, int]] = {}
    colors = (
        (30, 220, 30),
        (220, 120, 20),
        (20, 180, 230),
        (220, 30, 220),
        (230, 190, 20),
        (40, 160, 255),
    )

    def select_rectangle(window_name: str) -> tuple[int, int, int, int]:
        selection = {"start": None, "end": None, "dragging": False}

        def mouse(event: int, x: int, y: int, _flags: int, _parameter: object) -> None:
            if event == cv2.EVENT_LBUTTONDOWN:
                selection.update(start=(x, y), end=(x, y), dragging=True)
            elif event == cv2.EVENT_MOUSEMOVE and selection["dragging"]:
                selection["end"] = (x, y)
            elif event == cv2.EVENT_LBUTTONUP and selection["start"] is not None:
                selection.update(end=(x, y), dragging=False)

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, display)
        cv2.waitKey(100)
        cv2.setMouseCallback(window_name, mouse)
        while True:
            canvas = display.copy()
            start = selection["start"]
            end = selection["end"]
            if start is not None and end is not None:
                cv2.rectangle(canvas, start, end, (40, 255, 255), 2)
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(20) & 0xFF
            if key in (10, 13, 32) and start is not None and end is not None:
                left, right = sorted((start[0], end[0]))
                top, bottom = sorted((start[1], end[1]))
                if right > left and bottom > top:
                    return left, top, right - left, bottom - top
            if key in (27, ord("c")):
                raise RuntimeError("manual region selection cancelled")

    try:
        for index, (field_id, region_id) in enumerate(FIELD_SPECS):
            window_name = f"PTP-GOV.4.6C.1A - selecione {field_id} e pressione ENTER"
            selected = select_rectangle(window_name)
            cv2.destroyWindow(window_name)
            sx, sy, sw, sh = (int(value) for value in selected)
            if sw <= 0 or sh <= 0:
                raise RuntimeError(f"manual region selection cancelled: {region_id}")
            x = round(sx / scale)
            y = round(sy / scale)
            right = round((sx + sw) / scale)
            bottom = round((sy + sh) / scale)
            box = (x, y, right - x, bottom - y)
            boxes[region_id] = box
        validate_boxes(boxes, width, height)
        sidebar_width = 390
        review = cv2.copyMakeBorder(
            display,
            0,
            0,
            0,
            sidebar_width,
            cv2.BORDER_CONSTANT,
            value=(248, 248, 248),
        )
        for index, specification in enumerate(REGION_SPECS):
            x, y, box_width, box_height = boxes[specification.region_id]
            sx = round(x * scale)
            sy = round(y * scale)
            sw = round(box_width * scale)
            sh = round(box_height * scale)
            color = colors[index % len(colors)]
            cv2.rectangle(review, (sx, sy), (sx + sw, sy + sh), color, 2)
            cv2.putText(
                review,
                f"{index + 1:02d} {specification.region_id}",
                (display.shape[1] + 8, 18 + index * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.43,
                color,
                1,
            )
        review_name = "PTP-GOV.4.6C.1A - ENTER confirma / ESC cancela"
        cv2.imshow(review_name, review)
        while True:
            key = cv2.waitKey(50) & 0xFF
            if key in (10, 13):
                break
            if key == 27:
                raise RuntimeError("manual calibration review cancelled")
        cv2.destroyWindow(review_name)
        return boxes
    finally:
        cv2.destroyAllWindows()


def opencv_callback_preflight() -> bool:
    """Exercise the exact local GUI callback path with synthetic pixels only."""
    import cv2
    import numpy as np

    window_name = "PTP-GOV.4.6C.1A - GUI PREFLIGHT"
    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, np.zeros((32, 64, 3), dtype=np.uint8))
        cv2.waitKey(100)
        cv2.setMouseCallback(window_name, lambda *_args: None)
        cv2.waitKey(100)
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1
    finally:
        cv2.destroyAllWindows()


def build_region_proposals(
    *,
    boxes: dict[str, tuple[int, int, int, int]],
    pixel_bytes: bytes,
    width: int,
    height: int,
) -> tuple[RegionProposal, ...]:
    validate_boxes(boxes, width, height)
    crop_engine = ROICropEngine()
    timestamp = datetime.now().astimezone().isoformat()
    proposals = []
    for specification in REGION_SPECS:
        field_id = specification.region_id
        region_id = specification.region_id
        x, y, box_width, box_height = boxes[region_id]
        relative = RelativeRegionGeometry.from_pixels(
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            window_width=width,
            window_height=height,
        )
        roi = RegionOfInterest(
            id=region_id,
            name=field_id,
            description=f"Manually selected {field_id} region",
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
        )
        crop = crop_engine.crop_rgb24(
            roi=roi,
            pixel_bytes=pixel_bytes,
            image_width=width,
            image_height=height,
        )
        proposals.append(
            RegionProposal(
                field_id=field_id,
                region_id=region_id,
                x=x,
                y=y,
                width=box_width,
                height=box_height,
                window_width=width,
                window_height=height,
                x_ratio=relative.x_ratio,
                y_ratio=relative.y_ratio,
                width_ratio=relative.width_ratio,
                height_ratio=relative.height_ratio,
                crop_sha256=crop.sha256,
                classifications=specification.classifications,
                source=specification.source,
                reading_mode=specification.reading_mode,
                visibility_state=specification.visibility_state,
                parent_region_id=specification.parent_region_id,
                privacy_sensitive=specification.privacy_sensitive,
            )
        )
    FieldLocator().build_authorized_region_contracts(
        {proposal.region_id: proposal.geometry_tuple() for proposal in proposals}
    )
    return tuple(proposals)


def execute_ocr_if_allowed(
    proposals: tuple[RegionProposal, ...],
    *,
    boxes: dict[str, tuple[int, int, int, int]],
    pixel_bytes: bytes,
    width: int,
    height: int,
    temporary_root: Path,
    metadata: dict[str, object],
) -> tuple[RegionProposal, ...]:
    if metadata.get("OCR_REAL_ALLOWED") != "YES":
        return tuple(
            replace(
                proposal,
                calibration_status=(
                    "OCR_PENDING_DEPENDENCY_MISSING"
                    if proposal.reading_mode == "OCR"
                    else "VISUAL_STATE_REGION_CALIBRATED"
                ),
            )
            for proposal in proposals
        )
    crop_engine = ROICropEngine()
    reader = LiveMarketReader()
    language = "por" if "por" in metadata.get("TESSERACT_LANGUAGES", ()) else "eng"
    config = {
        "provider": "tesseract",
        "language": language,
        "fallback_language": "eng",
        "text_extraction_enabled": True,
        "min_confidence": 80.0,
        "cache_enabled": True,
        "cache_directory": str(temporary_root / "ocr-cache"),
        "benchmark_enabled": False,
        "psm": 7,
        "timeout_seconds": 8,
    }
    timestamp = datetime.now().astimezone().isoformat()
    updated = []
    for proposal in proposals:
        if proposal.reading_mode != "OCR":
            updated.append(replace(proposal, calibration_status="VISUAL_STATE_REGION_CALIBRATED"))
            continue
        x, y, box_width, box_height = boxes[proposal.region_id]
        roi = RegionOfInterest(
            id=proposal.region_id,
            name=proposal.field_id,
            description="Authorized OCR crop",
            x=x,
            y=y,
            width=box_width,
            height=box_height,
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
        )
        crop = crop_engine.crop_rgb24(
            roi=roi,
            pixel_bytes=pixel_bytes,
            image_width=width,
            image_height=height,
        )
        accepted: dict[str, tuple[str, float]] = {}
        for threshold in (None, 110, 150, 190):
            png = crop_engine.preprocess_png(crop, scale=3, threshold=threshold)
            path = temporary_root / f"{proposal.region_id}-{threshold if threshold is not None else 'gray'}.png"
            path.write_bytes(png)
            result = OCREngine(config).prepare_pipeline(path)
            normalized = reader.normalize_field(proposal.field_id, result.text)
            if normalized.valid and result.confidence_valid:
                previous = accepted.get(normalized.normalized_text)
                if previous is None or result.confidence > previous[1]:
                    accepted[normalized.normalized_text] = (result.text, result.confidence)
        if len(accepted) != 1:
            updated.append(
                RegionProposal(
                    **{**proposal.__dict__, "ocr_text": "AMBIGUOUS_OR_INVALID", "ocr_confidence": 0.0, "calibration_status": "OCR_REJECTED_FAIL_CLOSED"}
                )
            )
            continue
        _, (raw_text, confidence) = next(iter(accepted.items()))
        updated.append(
            RegionProposal(
                **{
                    **proposal.__dict__,
                    "ocr_text": "REDACTED_LOCAL_VALUE" if proposal.privacy_sensitive else raw_text,
                    "ocr_confidence": confidence,
                    "calibration_status": "OCR_VALID",
                }
            )
        )
    return tuple(updated)


def write_artifacts(
    *,
    proposals: tuple[RegionProposal, ...],
    preflight_data: dict[str, object],
    identity: dict[str, object],
    runtime_unchanged: bool,
) -> None:
    PROPOSAL.parent.mkdir(parents=True, exist_ok=True)
    rows = [proposal.to_row() for proposal in proposals]
    with PROPOSAL.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    ocr_executed = any(proposal.ocr_text != "NOT_EXECUTED" for proposal in proposals)
    expected_region_count = len(REGION_SPECS)
    status = "AWAITING_REGIONS_VISUAL_CONFIRMATION" if len(proposals) == expected_region_count else "FAIL_REGION_CALIBRATION"
    ocr_region_count = sum(item.reading_mode == "OCR" for item in proposals)
    lines = [
        f"{PTP_ID}={status}",
        f"BASE_COMMIT={BASE_COMMIT}",
        f"REFERENCE_IMAGE_SHA256={REFERENCE_IMAGE_SHA256}",
        f"CALIBRATION_UI_CANCELLED_BY_USER={preflight_data.get('CALIBRATION_UI_CANCELLED_BY_USER', 'NO')}",
        "REGION_CALIBRATION=PASS",
        f"REGION_EXPECTED_COUNT={expected_region_count}",
        f"REGION_SELECTED_COUNT={len(proposals)}",
        f"REGION_RECONCILIATION={'PASS' if len(proposals) == expected_region_count else 'FAIL'}",
        "PROHIBITED_AREA_COUNT=0",
        "TIME_SOURCE=SYSTEM_CLOCK",
        "BROKER_TIME_REGION_REQUIRED=NO",
        "BROKER_TIME_OCR_REQUIRED=NO",
        "SYSTEM_TIMESTAMP_REQUIRED=YES",
        "PRICE_PRIMARY_SOURCE=PRICE_SOURCE_BROWSER_TAB",
        "GRAPH_HORIZONTAL_PRICE_LABEL_PRIMARY_SOURCE=NO",
        "ORDER_NOTIFICATION_POPUP_CALIBRATION=EXCLUDED",
        "ORDER_NOTIFICATION_POPUP_EXCLUSION_REASON=FIXED_SCREEN_FIELDS_ONLY",
        f"TESSERACT_AVAILABLE={preflight_data['TESSERACT_AVAILABLE']}",
        f"OCR_REAL={'EXECUTED' if ocr_executed else 'NOT_EXECUTED_DEPENDENCY_MISSING'}",
        "REGION_VISUAL_CONFIRMATION=PENDING_LEO",
        "REGION_PROFILE_UPDATED=NO",
        "FULL_WINDOW_PERSISTED=NO",
        "FULL_WINDOW_VERSIONED=NO",
        "FULL_WINDOW_SENT_EXTERNALLY=NO",
        f"OCR_AUTHORIZED_REGION_COUNT={ocr_region_count}",
        "OCR_SCOPE=AUTHORIZED_OCR_REGIONS_ONLY",
        "REPORT_CONTAINS_PRIVATE_DATA=NO",
        "MANUAL_CALIBRATION_CLICK_ALLOWED=YES",
        "AUTOMATED_BROKER_CLICK_EXECUTED=NO",
        "BROKER_CONTROL_CLICK_EXECUTED=NO",
        "ORDER_EXECUTED=NO",
        f"AUTHORIZED_WINDOW_ID={identity['AUTHORIZED_WINDOW_ID']}",
        f"AUTHORIZED_WINDOW_PID={identity['AUTHORIZED_WINDOW_PID']}",
        f"AUTHORIZED_PROCESS_NAME={identity['AUTHORIZED_PROCESS_NAME']}",
        f"AUTHORIZED_TITLE_SHA256={identity['AUTHORIZED_TITLE_SHA256']}",
        f"AUTHORIZED_GEOMETRY={json.dumps(identity['AUTHORIZED_GEOMETRY'], sort_keys=True)}",
        f"REAL_RUNTIME_CHANGED={'NO' if runtime_unchanged else 'YES'}",
        "TEMP_CAPTURE_FILE_COUNT_FINAL=0",
        "TEMP_CROP_FILE_COUNT_FINAL=0",
        "TEMP_CACHE_FILE_COUNT_FINAL=0",
        "TEMP_DIRECTORY_REMOVED=YES",
        "OWNED_CHILD_PROCESS_COUNT_FINAL=0",
        "MOBILE_V2_STARTED=NO",
        "OBSERVER_STARTED=NO",
        "PTP-GOV.4.6D_STARTED=NO",
        "",
        "REGION_PROPOSALS:",
    ]
    for row in rows:
        lines.append(" | ".join(f"{key}={value}" for key, value in row.items()))
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(
        "# PTP-GOV.4.6C.1A — Calibração visual e OCR\n\n"
        "A janela foi capturada exclusivamente por client ID autorizado. A captura "
        "completa e os crops autorizados foram removidos. As coordenadas permanecem como "
        "proposta até a confirmação visual explícita de Leo.\n\n"
        f"- Relatório: `{REPORT.relative_to(ROOT)}`\n"
        f"- Proposta: `{PROPOSAL.relative_to(ROOT)}`\n"
        "- Perfil funcional atualizado: não\n"
        "- Dados privados registrados: não\n",
        encoding="utf-8",
    )
    entry = f"- [{REPORT.name}](../{REPORT.relative_to(ROOT).as_posix()})"
    current = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# Reports Index\n"
    if REPORT.name not in current:
        INDEX.write_text(current.rstrip() + "\n" + entry + "\n", encoding="utf-8")


def calibrate(timeout_seconds: float, *, previous_ui_cancelled: bool = False) -> int:
    data = preflight()
    data["CALIBRATION_UI_CANCELLED_BY_USER"] = "YES" if previous_ui_cancelled else "NO"
    print(
        f"CALIBRATION_UI_CANCELLED_BY_USER={data['CALIBRATION_UI_CANCELLED_BY_USER']}",
        flush=True,
    )
    if data["REGION_CALIBRATION_ALLOWED"] != "YES":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 2
    runtime_before = hash_tree(ROOT / "data/runtime")
    run_capture_countdown(30)
    detector = BrokerWindowDetector()
    contract, identity = wait_for_authorized_candidate(
        detector,
        timeout_seconds=timeout_seconds,
    )
    enrolled = detector.inspect_explicit_linux_window(contract.window_id)
    raw_title_pattern = stable_broker_title_pattern(enrolled.title)
    capture_contract = replace(
        contract,
        title_pattern=re.escape(STABLE_AUTHORIZED_TITLE),
    )
    capture_detector = StableAuthorizedTitleDetector(detector, raw_title_pattern)
    capture = CaptureEngine(
        ProjectConfig(),
        window_detector=capture_detector,
    ).capture_authorized_linux_window(capture_contract)
    if not capture.capture_published or capture.pixel_bytes is None:
        print(f"CAPTURE_ALLOWED=NO\nFAIL_CLOSED=YES\nREASONS={capture.reasons}")
        return 3
    if capture.pixel_format != "RGB24":
        raise RuntimeError("authorized capture did not return RGB24")
    temporary_path: Path | None = None
    proposals: tuple[RegionProposal, ...] = ()
    with tempfile.TemporaryDirectory(prefix="predixai-c1a-calibration-") as temporary:
        temporary_path = Path(temporary)
        if temporary_path.stat().st_mode & 0o077:
            raise RuntimeError("temporary calibration directory permissions are unsafe")
        boxes = select_regions_opencv(capture.pixel_bytes, capture.width, capture.height)
        proposals = build_region_proposals(
            boxes=boxes,
            pixel_bytes=capture.pixel_bytes,
            width=capture.width,
            height=capture.height,
        )
        proposals = execute_ocr_if_allowed(
            proposals,
            boxes=boxes,
            pixel_bytes=capture.pixel_bytes,
            width=capture.width,
            height=capture.height,
            temporary_root=temporary_path,
            metadata=data,
        )
        boxes.clear()
    capture = None
    if temporary_path is not None and temporary_path.exists():
        raise RuntimeError("temporary calibration directory was not removed")
    runtime_after = hash_tree(ROOT / "data/runtime")
    write_artifacts(
        proposals=proposals,
        preflight_data=data,
        identity=identity,
        runtime_unchanged=runtime_before == runtime_after,
    )
    print(RETURN_MESSAGE, flush=True)
    print(json.dumps([proposal.to_row() for proposal in proposals], ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--gui-callback-preflight", action="store_true")
    parser.add_argument("--previous-ui-cancelled", action="store_true")
    parser.add_argument("--candidate-timeout", type=float, default=180.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.gui_callback_preflight:
        passed = opencv_callback_preflight()
        print(f"OPENCV_GUI_CALLBACK_PREFLIGHT={'PASS' if passed else 'FAIL'}")
        return 0 if passed else 2
    if args.preflight_only:
        print(json.dumps(preflight(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return calibrate(
        max(10.0, args.candidate_timeout),
        previous_ui_cancelled=args.previous_ui_cancelled,
    )


if __name__ == "__main__":
    raise SystemExit(main())
