"""Live calibration mode for broker field calibration."""

from __future__ import annotations

import os
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
        lines = [
            f"Data e hora: {self.timestamp}",
            f"Janela detectada: {self.window_title}",
            "",
        ]
        for result in self.field_results:
            lines.append(f"{result.field_name.title()}: {result.text or 'UNKNOWN'}")
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
            CalibrationFieldBox("asset", 0.00, 0.00, 0.40, 0.22),
            CalibrationFieldBox("price", 0.30, 0.00, 0.35, 0.22),
            CalibrationFieldBox("time", 0.62, 0.00, 0.38, 0.22),
            CalibrationFieldBox("balance", 0.00, 0.72, 0.40, 0.28),
            CalibrationFieldBox("payout", 0.62, 0.18, 0.38, 0.28),
        )

    def run(
        self,
        *,
        countdown_seconds: int = 10,
        window_title: str = "unknown",
    ) -> CalibrationResult:
        started_at = time.perf_counter()
        print("Modo de calibração iniciado.")
        print("Você possui 10 segundos para colocar a corretora em primeiro plano.")
        for second in range(countdown_seconds, 0, -1):
            print(f"{second}...")
            time.sleep(1)

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
        self._open_artifacts(
            (
                result_path,
                full_frame / "screen.png",
                *(result.file_path for result in field_results),
            )
        )
        return calibration_result

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
        output_path.write_bytes(_encode_png_rgba(crop_width, crop_height, cropped))
        return SnapshotMetadata(
            session_id="calibration",
            captured_at=datetime.now().astimezone().isoformat(),
            resolution_width=crop_width,
            resolution_height=crop_height,
            file_path=output_path,
            file_size_bytes=output_path.stat().st_size,
            image_format="png",
        )


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
