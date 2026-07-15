#!/usr/bin/env python3
"""PTP-GOV.4.6C.1B.4 — real OCR validation for nine approved regions.

Safety properties:
- explicit active X11 window only;
- no automatic fallback selection;
- no clicks, orders, login, or broker interaction;
- screenshots and crops exist only in an ephemeral temporary directory;
- private raw and normalized values never leave process memory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import signal
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageEnhance, ImageGrab, ImageOps

from predixai.live.broker_window_detector import BrokerWindowDetector
from predixai.live.live_market_reader import LiveMarketReader
from predixai.ocr.ocr_engine import OCREngine

PTP_ID = "PTP-GOV.4.6C.1B.4"
EXPECTED_WINDOW_WIDTH = 1366
EXPECTED_WINDOW_HEIGHT = 768
EXPECTED_OCR_REGION_IDS = frozenset(
    {
        "ASSET",
        "PAYOUT",
        "PRICE_SOURCE_BROWSER_TAB",
        "TIMEFRAME",
        "ENTRY_VALUE",
        "DURATION",
        "PROFIT_DISPLAY",
        "ACCOUNT_BALANCE",
        "ACCOUNT_TYPE",
    }
)
PRIVATE_REGION_IDS = frozenset({"ACCOUNT_BALANCE", "ACCOUNT_TYPE"})
ALLOWED_PROCESSES = frozenset(
    {
        "chrome",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave",
        "brave-browser",
        "firefox",
        "firefox-bin",
        "microsoft-edge",
        "microsoft-edge-stable",
        "msedge",
    }
)
BROKER_BRAND_RE = re.compile(
    r"olymp\s*trade|olymptrade(?:\.com)?|iq\s*option|quotex|exnova|avalon|quadcode",
    re.IGNORECASE,
)
BROWSER_RE = re.compile(
    r"google\s+chrome|chromium|brave|firefox|microsoft\s+edge",
    re.IGNORECASE,
)
ASSET_RE = re.compile(
    r"\b[A-Z0-9]{2,12}/[A-Z0-9]{2,12}(?:\s+OTC)?\b|"
    r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*){0,3}\s+OTC\b|"
    r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*){0,4}\s+Index\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"(?<!\d)\d{2,6}(?:[.,]\d{1,6})(?!\d)")
GEOMETRY_RE = re.compile(r"^(?P<w>\d+)x(?P<h>\d+)\+(?P<x>-?\d+)\+(?P<y>-?\d+)$")


class ValidationFailure(RuntimeError):
    """Controlled fail-closed validation error."""


@dataclass(frozen=True)
class WindowSnapshot:
    window_id: str
    pid: int
    process_name: str
    title_sha256: str
    title_compatible: bool
    left: int
    top: int
    width: int
    height: int
    visible: bool
    minimized: bool
    foreground: bool
    fallback_used: bool

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RegionGeometry:
    region_id: str
    x: int
    y: int
    width: int
    height: int
    privacy_sensitive: bool


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def process_allowlisted(process_name: str) -> bool:
    normalized = Path((process_name or "").strip()).name.casefold()
    return normalized in ALLOWED_PROCESSES


def title_compatible(title: str) -> bool:
    text = (title or "").strip()
    broker = bool(BROKER_BRAND_RE.search(text))
    browser = bool(BROWSER_RE.search(text))
    asset = bool(ASSET_RE.search(text))
    price = bool(PRICE_RE.search(text))
    return (broker and asset) or (browser and asset and price)


def active_window_id() -> str:
    detector = BrokerWindowDetector()
    result = detector._command_runner(("xprop", "-root", "_NET_ACTIVE_WINDOW"))
    if result.returncode != 0:
        raise ValidationFailure("ACTIVE_WINDOW_QUERY_FAILED")
    match = re.search(r"#\s*(0x[0-9a-fA-F]+)", result.stdout or "")
    if match is None:
        raise ValidationFailure("ACTIVE_WINDOW_ID_NOT_FOUND")
    normalized = detector._normalize_window_id(match.group(1))
    if not normalized:
        raise ValidationFailure("ACTIVE_WINDOW_ID_INVALID")
    return normalized


def inspect_explicit_window(window_id: str) -> WindowSnapshot:
    state = BrokerWindowDetector().inspect_explicit_linux_window(window_id)
    metadata = state.metadata
    return WindowSnapshot(
        window_id=str(metadata.get("window_id") or ""),
        pid=int(metadata.get("window_pid") or 0),
        process_name=str(metadata.get("process_name") or "").strip(),
        title_sha256=sha256_text(state.title or ""),
        title_compatible=title_compatible(state.title or ""),
        left=int(state.left),
        top=int(state.top),
        width=int(state.resolution_width),
        height=int(state.resolution_height),
        visible=bool(metadata.get("window_visible")),
        minimized=bool(metadata.get("window_minimized")),
        foreground=bool(state.foreground),
        fallback_used=bool(metadata.get("fallback_used", True)),
    )


def window_authorized(snapshot: WindowSnapshot) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    if not process_allowlisted(snapshot.process_name):
        failures.append("PROCESS_ALLOWLIST_FAIL")
    if not snapshot.title_compatible:
        failures.append("BROKER_TITLE_COMPATIBLE_FAIL")
    if (snapshot.width, snapshot.height) != (
        EXPECTED_WINDOW_WIDTH,
        EXPECTED_WINDOW_HEIGHT,
    ):
        failures.append("WINDOW_GEOMETRY_EXPECTED_FAIL")
    if not snapshot.visible:
        failures.append("WINDOW_VISIBLE_FAIL")
    if snapshot.minimized:
        failures.append("WINDOW_MINIMIZED")
    if not snapshot.foreground:
        failures.append("FOREGROUND_FAIL")
    if snapshot.fallback_used:
        failures.append("AUTOMATIC_FALLBACK_USED")
    if snapshot.pid <= 0 or not snapshot.window_id:
        failures.append("WINDOW_IDENTITY_INCOMPLETE")
    return not failures, tuple(failures)


def window_stable(
    before: WindowSnapshot,
    after: WindowSnapshot,
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    for field_name in ("window_id", "pid", "process_name", "left", "top", "width", "height"):
        if getattr(before, field_name) != getattr(after, field_name):
            failures.append(f"WINDOW_{field_name.upper()}_CHANGED")
    authorized, auth_failures = window_authorized(after)
    if not authorized:
        failures.extend(auth_failures)
    return not failures, tuple(dict.fromkeys(failures))


def load_regions(tsv_path: Path) -> tuple[RegionGeometry, ...]:
    if not tsv_path.is_file() or tsv_path.is_symlink():
        raise ValidationFailure("APPROVED_TSV_NOT_REGULAR_FILE")
    with tsv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    if len(rows) != 16:
        raise ValidationFailure("APPROVED_REGION_TOTAL_NOT_16")

    seen: set[str] = set()
    ocr_regions: list[RegionGeometry] = []
    visual_count = 0

    for row in rows:
        field_id = str(row.get("FIELD_ID") or "").strip().upper()
        region_id = str(row.get("REGION_ID") or "").strip().upper()
        if not field_id or field_id != region_id or region_id in seen:
            raise ValidationFailure("APPROVED_TSV_ID_RECONCILIATION_FAIL")
        seen.add(region_id)

        try:
            row_window_width = int(str(row.get("WINDOW_WIDTH") or ""))
            row_window_height = int(str(row.get("WINDOW_HEIGHT") or ""))
        except ValueError as exc:
            raise ValidationFailure("APPROVED_TSV_WINDOW_GEOMETRY_INVALID") from exc
        if (row_window_width, row_window_height) != (
            EXPECTED_WINDOW_WIDTH,
            EXPECTED_WINDOW_HEIGHT,
        ):
            raise ValidationFailure("APPROVED_TSV_WINDOW_GEOMETRY_DRIFT")

        geometry_match = GEOMETRY_RE.fullmatch(
            str(row.get("PIXEL_GEOMETRY") or "").strip()
        )
        if geometry_match is None:
            raise ValidationFailure("APPROVED_TSV_PIXEL_GEOMETRY_INVALID")
        width = int(geometry_match.group("w"))
        height = int(geometry_match.group("h"))
        x = int(geometry_match.group("x"))
        y = int(geometry_match.group("y"))
        if min(x, y, width, height) < 0 or width <= 0 or height <= 0:
            raise ValidationFailure("APPROVED_TSV_REGION_GEOMETRY_INVALID")
        if x + width > EXPECTED_WINDOW_WIDTH or y + height > EXPECTED_WINDOW_HEIGHT:
            raise ValidationFailure("APPROVED_TSV_REGION_OUTSIDE_WINDOW")

        try:
            ratio_values = (
                float(str(row.get("x_ratio") or "")),
                float(str(row.get("y_ratio") or "")),
                float(str(row.get("width_ratio") or "")),
                float(str(row.get("height_ratio") or "")),
            )
        except ValueError as exc:
            raise ValidationFailure("APPROVED_TSV_RATIO_INVALID") from exc
        expected_pixels = (
            round(ratio_values[0] * EXPECTED_WINDOW_WIDTH),
            round(ratio_values[1] * EXPECTED_WINDOW_HEIGHT),
            round(ratio_values[2] * EXPECTED_WINDOW_WIDTH),
            round(ratio_values[3] * EXPECTED_WINDOW_HEIGHT),
        )
        actual_pixels = (x, y, width, height)
        if any(abs(expected - actual) > 1 for expected, actual in zip(expected_pixels, actual_pixels)):
            raise ValidationFailure("APPROVED_TSV_RATIO_PIXEL_MISMATCH")

        reading_mode = str(row.get("READING_MODE") or "").strip().upper()
        privacy_sensitive = (
            str(row.get("PRIVACY_SENSITIVE") or "").strip().upper() == "YES"
        )
        if reading_mode == "OCR":
            if region_id not in EXPECTED_OCR_REGION_IDS:
                raise ValidationFailure("UNEXPECTED_OCR_REGION")
            if privacy_sensitive != (region_id in PRIVATE_REGION_IDS):
                raise ValidationFailure("PRIVATE_REGION_FLAG_MISMATCH")
            ocr_regions.append(
                RegionGeometry(
                    region_id=region_id,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    privacy_sensitive=privacy_sensitive,
                )
            )
        elif reading_mode == "VISUAL_STATE":
            visual_count += 1
        else:
            raise ValidationFailure("UNSUPPORTED_READING_MODE")

    if {region.region_id for region in ocr_regions} != EXPECTED_OCR_REGION_IDS:
        raise ValidationFailure("OCR_REGION_SET_MISMATCH")
    if len(ocr_regions) != 9 or visual_count != 7:
        raise ValidationFailure("OCR_VISUAL_REGION_COUNT_MISMATCH")
    return tuple(sorted(ocr_regions, key=lambda item: item.region_id))


def capture_window(snapshot: WindowSnapshot) -> Image.Image:
    bbox = (
        snapshot.left,
        snapshot.top,
        snapshot.left + snapshot.width,
        snapshot.top + snapshot.height,
    )
    try:
        image = ImageGrab.grab(
            bbox=bbox,
            xdisplay=os.environ.get("DISPLAY"),
        )
    except Exception as exc:
        raise ValidationFailure(f"WINDOW_CAPTURE_FAILED_{type(exc).__name__}") from exc
    image = image.convert("RGB")
    if image.size != (snapshot.width, snapshot.height):
        raise ValidationFailure("WINDOW_CAPTURE_SIZE_MISMATCH")
    return image


def preprocessing_variants(crop: Image.Image, region_id: str) -> tuple[tuple[str, Image.Image], ...]:
    scale_map = {
        "PAYOUT": 10,
        "PRICE_SOURCE_BROWSER_TAB": 8,
        "TIMEFRAME": 9,
        "ACCOUNT_TYPE": 10,
    }
    scale = scale_map.get(region_id, 7)
    gray = ImageOps.grayscale(crop)
    resized = gray.resize(
        (max(1, gray.width * scale), max(1, gray.height * scale)),
        Image.Resampling.LANCZOS,
    )
    contrast = ImageOps.autocontrast(resized)
    sharpened = ImageEnhance.Sharpness(contrast).enhance(2.0)
    variants: list[tuple[str, Image.Image]] = [
        ("gray", resized),
        ("autocontrast", contrast),
        ("sharpened", sharpened),
    ]
    for threshold in (105, 145, 185):
        variants.append(
            (
                f"threshold_{threshold}",
                contrast.point(lambda value, t=threshold: 255 if value >= t else 0),
            )
        )
    return tuple(variants)


def psm_for_region(region_id: str) -> int:
    if region_id in {"PAYOUT", "TIMEFRAME"}:
        return 8
    return 7


def public_region_result(
    *,
    region_id: str,
    privacy_sensitive: bool,
    passed: bool,
    status: str,
    pipeline_ready: bool,
    confidence: float,
    language_used: str,
    normalization_valid: bool,
    normalized_value: str,
    variant: str,
    reasons: tuple[str, ...],
) -> dict[str, object]:
    return {
        "region_id": region_id,
        "privacy_sensitive": privacy_sensitive,
        "pass": passed,
        "status": status,
        "pipeline_ready": pipeline_ready,
        "confidence": round(float(confidence), 3),
        "language_used": language_used,
        "normalization_valid": normalization_valid,
        "normalized_value": (
            "REDACTED"
            if privacy_sensitive
            else (normalized_value if passed else "")
        ),
        "variant": variant,
        "reasons": list(dict.fromkeys(reasons)),
    }


def validate_one_region(
    full_image: Image.Image,
    region: RegionGeometry,
    temporary_directory: Path,
) -> dict[str, object]:
    crop = full_image.crop(
        (
            region.x,
            region.y,
            region.x + region.width,
            region.y + region.height,
        )
    )
    reader = LiveMarketReader()
    candidates: list[dict[str, object]] = []

    for variant_name, variant_image in preprocessing_variants(crop, region.region_id):
        variant_path = temporary_directory / f"{region.region_id}_{variant_name}.png"
        variant_image.save(variant_path, format="PNG", optimize=False)
        engine = OCREngine(
            {
                "provider": "tesseract",
                "language": "por",
                "fallback_language": "eng",
                "text_extraction_enabled": True,
                "min_confidence": 80.0,
                "cache_enabled": False,
                "privacy_sensitive": region.privacy_sensitive,
                "psm": psm_for_region(region.region_id),
                "timeout_seconds": 12,
                "benchmark_enabled": False,
            }
        )
        try:
            ocr_result = engine.prepare_pipeline(variant_path)
            normalization = reader.normalize_field(region.region_id, ocr_result.text)
            reasons = tuple(ocr_result.validation_errors) + tuple(
                ocr_result.validation_warnings
            ) + tuple(normalization.reasons)
            passed = bool(ocr_result.pipeline_ready and normalization.valid)
            candidates.append(
                {
                    "passed": passed,
                    "status": ocr_result.status,
                    "pipeline_ready": ocr_result.pipeline_ready,
                    "confidence": ocr_result.confidence,
                    "language_used": ocr_result.language_used,
                    "normalization_valid": normalization.valid,
                    "normalized_value": normalization.normalized_text,
                    "variant": variant_name,
                    "reasons": reasons,
                }
            )
        except Exception as exc:
            candidates.append(
                {
                    "passed": False,
                    "status": f"EXECUTOR_ERROR_{type(exc).__name__}",
                    "pipeline_ready": False,
                    "confidence": 0.0,
                    "language_used": "",
                    "normalization_valid": False,
                    "normalized_value": "",
                    "variant": variant_name,
                    "reasons": (f"CONTROLLED_EXCEPTION_{type(exc).__name__}",),
                }
            )
        finally:
            variant_path.unlink(missing_ok=True)

    passing = [candidate for candidate in candidates if bool(candidate["passed"])]
    pool = passing or candidates
    best = max(
        pool,
        key=lambda candidate: (
            bool(candidate["passed"]),
            float(candidate["confidence"]),
        ),
    )
    return public_region_result(
        region_id=region.region_id,
        privacy_sensitive=region.privacy_sensitive,
        passed=bool(best["passed"]),
        status=str(best["status"]),
        pipeline_ready=bool(best["pipeline_ready"]),
        confidence=float(best["confidence"]),
        language_used=str(best["language_used"]),
        normalization_valid=bool(best["normalization_valid"]),
        normalized_value=str(best["normalized_value"]),
        variant=str(best["variant"]),
        reasons=tuple(str(item) for item in best["reasons"]),
    )


def invalidate_region_results(
    results: list[dict[str, object]],
    reason: str,
) -> list[dict[str, object]]:
    invalidated: list[dict[str, object]] = []
    for result in results:
        updated = dict(result)
        updated["pass"] = False
        updated["pipeline_ready"] = False
        updated["normalization_valid"] = False
        updated["normalized_value"] = (
            "REDACTED" if bool(updated["privacy_sensitive"]) else ""
        )
        updated["reasons"] = list(
            dict.fromkeys([*list(updated.get("reasons") or []), reason])
        )
        invalidated.append(updated)
    return invalidated


def result_skeleton(status: str = "FAIL") -> dict[str, object]:
    return {
        "ptp_id": PTP_ID,
        "final_status": status,
        "fail_reason": "NONE",
        "window_authorization": "NOT_RUN",
        "window_identity_stable_t1": "NOT_RUN",
        "window_identity_stable_t2": "NOT_RUN",
        "approved_region_total": 16,
        "real_ocr_region_count": 0,
        "real_ocr_region_pass_count": 0,
        "private_region_redaction": "NOT_RUN",
        "region_results": [],
        "window_t0": None,
        "window_t1": None,
        "window_t2": None,
        "safety": {
            "simulation_only": True,
            "real_login": False,
            "real_order": False,
            "broker_click": False,
            "auto_click": False,
            "real_balance_use": False,
            "screenshots_versioned": False,
            "persistent_cache": False,
            "raw_private_text_persisted": False,
            "normalized_private_value_persisted": False,
        },
    }


def perform_validation(tsv_path: Path, work_directory: Path) -> dict[str, object]:
    result = result_skeleton()
    try:
        regions = load_regions(tsv_path)
        result["real_ocr_region_count"] = len(regions)

        selected_window_id = active_window_id()
        t0 = inspect_explicit_window(selected_window_id)
        result["window_t0"] = t0.public_dict()
        authorized, auth_failures = window_authorized(t0)
        result["window_authorization"] = "PASS" if authorized else "FAIL"
        if not authorized:
            raise ValidationFailure(
                "WINDOW_AUTHORIZATION_FAIL_" + "_".join(auth_failures)
            )

        full_image = capture_window(t0)
        t1 = inspect_explicit_window(selected_window_id)
        result["window_t1"] = t1.public_dict()
        stable_t1, stable_t1_failures = window_stable(t0, t1)
        result["window_identity_stable_t1"] = "PASS" if stable_t1 else "FAIL"
        if not stable_t1:
            raise ValidationFailure(
                "WINDOW_IDENTITY_T1_FAIL_" + "_".join(stable_t1_failures)
            )

        region_results = [
            validate_one_region(full_image, region, work_directory)
            for region in regions
        ]
        full_image.close()

        t2 = inspect_explicit_window(selected_window_id)
        result["window_t2"] = t2.public_dict()
        stable_t2, stable_t2_failures = window_stable(t0, t2)
        result["window_identity_stable_t2"] = "PASS" if stable_t2 else "FAIL"
        if not stable_t2:
            region_results = invalidate_region_results(
                region_results,
                "WINDOW_IDENTITY_CHANGED_DURING_OCR",
            )

        private_safe = all(
            item["normalized_value"] == "REDACTED"
            and "raw_text" not in item
            for item in region_results
            if bool(item["privacy_sensitive"])
        )
        result["private_region_redaction"] = "PASS" if private_safe else "FAIL"
        result["region_results"] = region_results
        pass_count = sum(1 for item in region_results if bool(item["pass"]))
        result["real_ocr_region_pass_count"] = pass_count

        all_pass = (
            result["window_authorization"] == "PASS"
            and result["window_identity_stable_t1"] == "PASS"
            and result["window_identity_stable_t2"] == "PASS"
            and private_safe
            and len(region_results) == 9
            and pass_count == 9
        )
        result["final_status"] = "PASS" if all_pass else "FAIL"
        result["fail_reason"] = (
            "NONE"
            if all_pass
            else "ONE_OR_MORE_REAL_OCR_REGIONS_FAILED_OR_WINDOW_CHANGED"
        )
    except ValidationFailure as exc:
        result["final_status"] = "FAIL"
        result["fail_reason"] = str(exc)
    except Exception as exc:
        result["final_status"] = "FAIL"
        result["fail_reason"] = f"UNEXPECTED_{type(exc).__name__}"
    return result


def atomic_write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def render_page(token: str, status: str = "READY", result: dict[str, object] | None = None) -> bytes:
    rows = ""
    if result:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(item['region_id']))}</td>"
            f"<td>{'PASS' if item['pass'] else 'FAIL'}</td>"
            f"<td>{html.escape(str(item['confidence']))}</td>"
            f"<td>{html.escape(str(item['normalized_value']))}</td>"
            "</tr>"
            for item in result.get("region_results", [])
        )
    body = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PredixAI B4</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px}}
button{{font-size:20px;padding:16px;width:100%}}
table{{border-collapse:collapse;width:100%;margin-top:18px}}
td,th{{border:1px solid #bbb;padding:8px;text-align:left}}
</style>
</head>
<body>
<h1>PTP-GOV.4.6C.1B.4</h1>
<p>Status: <strong>{html.escape(status)}</strong></p>
<p>Mantenha a corretora aberta, visível, em primeiro plano e não toque no notebook durante o OCR.</p>
<form method="post" action="/capture">
<input type="hidden" name="token" value="{html.escape(token)}">
<button type="submit">Capturar e validar 9 regiões OCR</button>
</form>
<table>
<thead><tr><th>Região</th><th>Status</th><th>Confiança</th><th>Valor</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""
    return body.encode("utf-8")


def serve_mobile(
    *,
    port: int,
    token: str,
    result_json: Path,
    tsv_path: Path,
    timeout_seconds: int,
) -> int:
    state: dict[str, object] = {"started": False, "result": None}
    state_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "PredixAIB4/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, status: HTTPStatus, payload: bytes) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            supplied = parse_qs(parsed.query).get("token", [""])[0]
            if parsed.path != "/" or not secrets.compare_digest(supplied, token):
                self._send(HTTPStatus.FORBIDDEN, b"Forbidden")
                return
            result = state.get("result")
            status = "READY" if result is None else str(result.get("final_status"))
            self._send(
                HTTPStatus.OK,
                render_page(token, status=status, result=result if isinstance(result, dict) else None),
            )

        def do_POST(self) -> None:
            if self.path != "/capture":
                self._send(HTTPStatus.NOT_FOUND, b"Not found")
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > 4096:
                self._send(HTTPStatus.BAD_REQUEST, b"Bad request")
                return
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            supplied = parse_qs(body).get("token", [""])[0]
            if not secrets.compare_digest(supplied, token):
                self._send(HTTPStatus.FORBIDDEN, b"Forbidden")
                return

            with state_lock:
                if bool(state["started"]):
                    self._send(HTTPStatus.CONFLICT, b"Capture already started")
                    return
                state["started"] = True

            temporary_root = Path(
                tempfile.mkdtemp(
                    prefix="predixai_b4_capture_",
                    dir=str(result_json.parent),
                )
            )
            os.chmod(temporary_root, 0o700)
            try:
                result = perform_validation(tsv_path, temporary_root)
            finally:
                shutil.rmtree(temporary_root, ignore_errors=True)
            state["result"] = result
            atomic_write_json(result_json, result)
            self._send(
                HTTPStatus.OK,
                render_page(
                    token,
                    status=str(result.get("final_status")),
                    result=result,
                ),
            )
            threading.Thread(
                target=self.server.shutdown,
                daemon=True,
            ).start()

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.daemon_threads = True
    timer = threading.Timer(timeout_seconds, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        timer.cancel()
        server.server_close()

    if not result_json.exists():
        timeout_result = result_skeleton(status="PAUSE")
        timeout_result["fail_reason"] = "MOBILE_TRIGGER_TIMEOUT"
        atomic_write_json(result_json, timeout_result)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--tsv", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("invalid port")
    if len(args.token) < 20:
        raise SystemExit("invalid token")
    return serve_mobile(
        port=args.port,
        token=args.token,
        result_json=args.result_json.resolve(),
        tsv_path=args.tsv.resolve(),
        timeout_seconds=args.timeout_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
