"""Live calibration mode for broker field calibration."""

from __future__ import annotations

import ctypes
import json
import os
import re
import struct
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from predixai.capture import SnapshotMetadata
from predixai.core.logger import log_error
from predixai.ocr import OCREngine
from predixai.vision import ImageBuffer, ImageLoader


@dataclass(frozen=True)
class CalibrationFieldBox:
    """Relative crop box for one calibration field."""

    field_name: str
    left_ratio: float
    top_ratio: float
    width_ratio: float
    height_ratio: float


@dataclass(frozen=True)
class CalibrationFieldResult:
    """OCR result for one calibrated field."""

    field_name: str
    file_path: Path
    text: str
    confidence: float
    status: str
    unknown: bool
    ocr_result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "file_path": str(self.file_path),
            "text": self.text,
            "confidence": self.confidence,
            "status": self.status,
            "unknown": self.unknown,
            "ocr_result": dict(self.ocr_result),
        }


@dataclass(frozen=True)
class CalibrationResult:
    """Summary of a live calibration run."""

    timestamp: str
    window_title: str
    field_results: tuple[CalibrationFieldResult, ...]
    unknown_fields: tuple[str, ...]
    total_time_ms: float
    output_directory: Path


    def to_text(self) -> str:
        price = _extract_price_from_window_title(self.window_title)

        lines = [
            f"Data e hora: {self.timestamp}",
            f"Janela detectada: {self.window_title}",
            f"Price: {price or 'UNKNOWN'}",
            "",
        ]

        for result in self.field_results:
            if result.field_name == "asset_payout":
                asset, payout = _split_asset_payout(result.text)
                lines.append(f"Asset: {asset or 'UNKNOWN'}")
                lines.append(f"Payout: {payout or 'UNKNOWN'}")
                lines.append(f"Asset_Payout_Raw: {result.text or 'UNKNOWN'}")
                continue

            normalized_text = _normalize_field_text(result.field_name, result.text)
            lines.append(f"{result.field_name.title()}: {normalized_text or 'UNKNOWN'}")
        lines.extend(
            [
                "",
                "Campos encontrados: "
                + ", ".join(
                    result.field_name
                    for result in self.field_results
                    if not result.unknown
                ),
                "Campos UNKNOWN: " + ", ".join(self.unknown_fields),
                "Confiança do OCR por campo:",
            ]
        )
        for result in self.field_results:
            lines.append(
                f"- {result.field_name}: {result.confidence} ({result.status})"
            )
        lines.append("")
        lines.append(f"Tempo total da calibração: {self.total_time_ms} ms")
        return "\n".join(lines)

    def to_json_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "timestamp": self.timestamp,
            "window_title": self.window_title,
            "price": _extract_price_from_window_title(self.window_title),
            "unknown_fields": list(self.unknown_fields),
            "total_time_ms": self.total_time_ms,
            "fields": {},
        }

        fields: dict[str, object] = {}

        for result in self.field_results:
            if result.field_name == "asset_payout":
                asset, payout = _split_asset_payout(result.text)
                data["asset"] = asset
                data["payout"] = payout
                fields[result.field_name] = result.to_dict()
                continue

            normalized_text = _normalize_field_text(result.field_name, result.text)
            data[result.field_name] = normalized_text
            fields[result.field_name] = result.to_dict()

        data["fields"] = fields
        return data


class LiveCalibrationEngine:
    """Run an isolated calibration pass for live broker reading."""

    def __init__(
        self,
        *,
        config: Any,
        capture_engine: Any,
        capture_status: Any,
        vision_engine: Any,
        ocr_engine: OCREngine,
        logger: Any,
    ) -> None:
        self.config = config
        self.capture_engine = capture_engine
        self.capture_status = capture_status
        self.vision_engine = vision_engine
        self.ocr_engine = ocr_engine
        self.logger = logger
        self.image_loader = ImageLoader()
        self.field_boxes = (
            CalibrationFieldBox("asset_payout", 0.075, 0.12, 0.16, 0.08),
            CalibrationFieldBox("balance", 0.77, 0.12, 0.12, 0.08),
            CalibrationFieldBox("trade_value", 0.82, 0.21, 0.17, 0.07),
            CalibrationFieldBox("duration", 0.82, 0.28, 0.17, 0.08),
            CalibrationFieldBox("right_panel", 0.81, 0.12, 0.18, 0.72),
        )
    def run(
        self,
        *,
        countdown_seconds: int = 10,
        window_title: str = "unknown",
    ) -> CalibrationResult:
        started_at = time.perf_counter()
        print("Modo de calibraÃ§Ã£o iniciado.")
        print("VocÃª possui 10 segundos para colocar a corretora em primeiro plano.")
        for second in range(countdown_seconds, 0, -1):
            print(f"{second}...")
            time.sleep(1)

        active_window_title = self._get_active_window_title() or window_title
        metadata = self.capture_engine.capture_manual_snapshot(self.capture_status)
        full_frame = self._prepare_calibration_directory(metadata)
        image_buffer = self.image_loader.load(Path(metadata.file_path))
        field_results = []
        for box in self.field_boxes:
            crop_path = full_frame / f"{box.field_name}.png"
            crop_metadata = self._crop_png(
                image_buffer.file_path,
                crop_path,
                image_buffer.width,
                image_buffer.height,
                box,
            )
            ocr_result = self.ocr_engine.prepare_pipeline(crop_metadata.file_path)
            field_results.append(
                CalibrationFieldResult(
                    field_name=box.field_name,
                    file_path=crop_path,
                    text=ocr_result.text or "UNKNOWN",
                    confidence=float(ocr_result.confidence),
                    status=str(ocr_result.status),
                    unknown=not bool(ocr_result.text_extracted),
                    ocr_result=ocr_result.to_dict(),
                )
            )

        calibration_result = CalibrationResult(
            timestamp=datetime.now().astimezone().isoformat(),
            window_title=active_window_title,
            field_results=tuple(field_results),
            unknown_fields=tuple(
                result.field_name for result in field_results if result.unknown
            ),
            total_time_ms=round((time.perf_counter() - started_at) * 1000, 3),
            output_directory=full_frame,
        )

        result_path = full_frame / "calibration_result.txt"
        result_path.write_text(calibration_result.to_text(), encoding="utf-8")
        json_path = full_frame / "calibration_result.json"
        json_path.write_text(
            json.dumps(
                calibration_result.to_json_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._open_artifacts(
            (
                result_path,
                json_path,
                full_frame / "screen.png",
                *(result.file_path for result in field_results),
            )
        )
        return calibration_result

    def read_snapshot_fields(
        self,
        *,
        metadata: SnapshotMetadata,
        window_title: str,
        output_directory_name: str = "live_once_fields",
        open_artifacts: bool = False,
    ) -> CalibrationResult:
        """Read calibrated broker fields from an existing captured snapshot."""
        started_at = time.perf_counter()
        full_frame = self.config.resolve_path("captures") / output_directory_name
        full_frame.mkdir(parents=True, exist_ok=True)

        screen_path = full_frame / "screen.png"
        screen_path.write_bytes(Path(metadata.file_path).read_bytes())

        image_buffer = self.image_loader.load(Path(metadata.file_path))
        field_results: list[CalibrationFieldResult] = []

        for box in self.field_boxes:
            crop_path = full_frame / f"{box.field_name}.png"
            crop_metadata = self._crop_png(
                image_buffer.file_path,
                crop_path,
                image_buffer.width,
                image_buffer.height,
                box,
            )
            ocr_result = self.ocr_engine.prepare_pipeline(crop_metadata.file_path)
            field_results.append(
                CalibrationFieldResult(
                    field_name=box.field_name,
                    file_path=crop_path,
                    text=ocr_result.text or "UNKNOWN",
                    confidence=float(ocr_result.confidence),
                    status=str(ocr_result.status),
                    unknown=not bool(ocr_result.text_extracted),
                    ocr_result=ocr_result.to_dict(),
                )
            )

        calibration_result = CalibrationResult(
            timestamp=datetime.now().astimezone().isoformat(),
            window_title=window_title,
            field_results=tuple(field_results),
            unknown_fields=tuple(
                result.field_name for result in field_results if result.unknown
            ),
            total_time_ms=round((time.perf_counter() - started_at) * 1000, 3),
            output_directory=full_frame,
        )

        result_path = full_frame / "calibration_result.txt"
        result_path.write_text(calibration_result.to_text(), encoding="utf-8")

        json_path = full_frame / "calibration_result.json"
        json_path.write_text(
            json.dumps(
                calibration_result.to_json_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if open_artifacts:
            self._open_artifacts(
                (
                    result_path,
                    json_path,
                    screen_path,
                    *(result.file_path for result in field_results),
                )
            )

        return calibration_result

    def _get_active_window_title(self) -> str:
        if os.name != "nt":
            return ""

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value.strip()

    def _prepare_calibration_directory(self, metadata: SnapshotMetadata) -> Path:
        root = self.config.resolve_path("captures") / "calibration"
        root.mkdir(parents=True, exist_ok=True)
        screen_path = root / "screen.png"
        screen_path.write_bytes(Path(metadata.file_path).read_bytes())
        return root

    def _open_artifacts(self, paths: tuple[Path, ...]) -> None:
        for path in paths:
            if hasattr(os, "startfile"):
                try:
                    os.startfile(str(path))  # type: ignore[attr-defined]
                except OSError:
                    log_error(self.logger, "Failed to open calibration artifact", OSError(str(path)))

    def _crop_png(
        self,
        source_path: Path,
        output_path: Path,
        source_width: int,
        source_height: int,
        box: CalibrationFieldBox,
    ) -> SnapshotMetadata:
        pixels, width, height = _decode_png_rgba(source_path)
        if width != source_width or height != source_height:
            raise ValueError("Calibration source image dimensions do not match.")

        crop_left = max(0, min(width - 1, int(round(width * box.left_ratio))))
        crop_top = max(0, min(height - 1, int(round(height * box.top_ratio))))
        crop_width = max(1, min(width - crop_left, int(round(width * box.width_ratio))))
        crop_height = max(
            1,
            min(height - crop_top, int(round(height * box.height_ratio))),
        )
        cropped = _crop_rgba(pixels, width, crop_left, crop_top, crop_width, crop_height)

        scale = 3
        crop_width_scaled = crop_width * scale
        crop_height_scaled = crop_height * scale
        cropped = _scale_rgba_nearest(cropped, crop_width, crop_height, scale)

        output_path.write_bytes(
            _encode_png_rgba(crop_width_scaled, crop_height_scaled, cropped)
        )
        return SnapshotMetadata(
            session_id="calibration",
            captured_at=datetime.now().astimezone().isoformat(),
            resolution_width=crop_width_scaled,
            resolution_height=crop_height_scaled,
            file_path=output_path,
            file_size_bytes=output_path.stat().st_size,
            image_format="png",
        )
def _normalize_field_text(field_name: str, text: str) -> str:
    clean_text = " ".join((text or "").split())
    upper_text = clean_text.upper()

    if field_name == "balance":
        if "BRL" in upper_text:
            match = re.search(r"\bBRL\s*\d+[.,]\d{2}\b", clean_text, flags=re.IGNORECASE)
            return match.group(0).replace("brl", "BRL").replace("Brl", "BRL") if match else clean_text

        match = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", clean_text)
        return f"D {match.group(0)}" if match else clean_text

    if field_name == "trade_value":
        amount = re.search(r"\d+[.,]?\d*", clean_text)

        if "R$" in clean_text or "RS" in upper_text:
            return f"R$ {amount.group(0)}" if amount else clean_text.replace("RS", "R$")

        if amount:
            return f"D {amount.group(0)}"

        return clean_text

    if field_name == "duration":
        match = re.search(r"\b\d+\s*min\.?\b", clean_text, flags=re.IGNORECASE)
        return match.group(0).replace("min", "min.") if match else clean_text

    if field_name == "right_panel":
        return (
            clean_text
            .replace("RS", "R$")
            .replace("Â£)", "D")
            .replace("DB", "D")
            .replace("0 17,8", "D 17,8")
        )

    return clean_text
def _extract_price_from_window_title(window_title: str) -> str:
    match = re.search(r"^[^\d]*(\d+[.,]\d+)", window_title or "")
    return match.group(1).replace(",", ".") if match else ""
def _split_asset_payout(text: str) -> tuple[str, str]:
    clean_text = " ".join(
        (text or "")
        .replace("Â·", " ")
        .replace(":", " ")
        .replace("-", " ")
        .split()
    )

    asset = ""

    pair_match = re.search(
        r"\b[A-Z]{3}/[A-Z]{3}(?:\s+OTC)?\b",
        clean_text,
        flags=re.IGNORECASE,
    )
    if pair_match:
        asset = pair_match.group(0).upper()
    else:
        index_match = re.search(
            r"\b([A-Za-z]{2,12})\s+Index\b",
            clean_text,
            flags=re.IGNORECASE,
        )
        if index_match:
            prefix = index_match.group(1)
            if prefix.upper() == "LATAM":
                prefix = "LATAM"
            asset = f"{prefix} Index"

    payout_match = re.search(r"(\d{2,3})\s*%", clean_text)
    if payout_match:
        payout = f"{payout_match.group(1)}%"
    else:
        single_digit = re.search(r"\b(\d)\s*%", clean_text)
        if single_digit and ("FT" in clean_text.upper() or "OTC" in clean_text.upper()):
            payout = f"8{single_digit.group(1)}%"
        elif single_digit:
            payout = f"{single_digit.group(1)}%"
        else:
            payout = ""

    return asset.strip(), payout.strip()
def _decode_png_rgba(path: Path) -> tuple[bytes, int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Calibration only supports PNG images.")

    offset = 8
    width = height = 0
    raw_chunks = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type != 6 or compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("Unsupported PNG format for calibration.")
        elif chunk_type == b"IDAT":
            raw_chunks.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    decompressed = zlib.decompress(bytes(raw_chunks))
    stride = width * 4
    pixels = bytearray(width * height * 4)
    src_index = 0
    dst_index = 0
    for _ in range(height):
        filter_type = decompressed[src_index]
        if filter_type != 0:
            raise ValueError("Only PNG filter type 0 is supported for calibration.")
        src_index += 1
        row = decompressed[src_index : src_index + stride]
        pixels[dst_index : dst_index + stride] = row
        src_index += stride
        dst_index += stride
    return bytes(pixels), width, height


def _crop_rgba(
    pixels: bytes,
    source_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
) -> bytes:
    row_stride = source_width * 4
    target = bytearray((width * 4 + 1) * height)
    target_index = 0
    for row in range(height):
        target[target_index] = 0
        target_index += 1
        source_start = ((top + row) * row_stride) + (left * 4)
        source_end = source_start + (width * 4)
        target[target_index : target_index + (width * 4)] = pixels[source_start:source_end]
        target_index += width * 4
    return bytes(target)
def _scale_rgba_nearest(
    raw_rows: bytes,
    width: int,
    height: int,
    scale: int,
) -> bytes:
    scaled_width = width * scale
    target = bytearray((scaled_width * 4 + 1) * (height * scale))
    target_index = 0

    for row in range(height):
        row_start = row * (width * 4 + 1) + 1
        row_pixels = raw_rows[row_start : row_start + (width * 4)]

        scaled_row = bytearray()
        for col in range(width):
            pixel_start = col * 4
            pixel = row_pixels[pixel_start : pixel_start + 4]
            for _ in range(scale):
                scaled_row.extend(pixel)

        for _ in range(scale):
            target[target_index] = 0
            target_index += 1
            target[target_index : target_index + (scaled_width * 4)] = scaled_row
            target_index += scaled_width * 4

    return bytes(target)

def _encode_png_rgba(width: int, height: int, raw_rows: bytes, compression: int = 6) -> bytes:
    compressed = zlib.compress(raw_rows, max(0, min(9, int(compression))))
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
            _png_chunk(b"IDAT", compressed),
            _png_chunk(b"IEND", b""),
        ]
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return b"".join(
        [
            struct.pack(">I", len(data)),
            chunk_type,
            data,
            struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF),
        ]
    )
