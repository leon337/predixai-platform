"""Manual screen snapshot writer for the Capture Engine."""

from __future__ import annotations

import ctypes
import hashlib
import os
import platform
import re
import stat
import struct
import subprocess
import zlib
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Callable, Sequence

_BI_RGB = 0
_DIB_RGB_COLORS = 0
_SM_CXVIRTUALSCREEN = 78
_SM_CYVIRTUALSCREEN = 79
_SM_XVIRTUALSCREEN = 76
_SM_YVIRTUALSCREEN = 77
_SRCCOPY = 0x00CC0020


@dataclass(frozen=True)
class ManualSnapshotResult:
    """Result of writing one manual snapshot file."""

    width: int
    height: int
    file_size_bytes: int


class ManualScreenSnapshot:
    """Capture one full-screen snapshot without image interpretation."""

    def capture(self, output_path: Path, compression: int) -> ManualSnapshotResult:
        """Write a single PNG snapshot and return basic file metadata."""
        if platform.system() != "Windows":
            raise RuntimeError(
                "Manual screen snapshot is available only on Windows."
            )

        width, height, image_buffer = _capture_windows_screen()
        png_data = _encode_png(width, height, image_buffer, compression)
        output_path.write_bytes(png_data)

        return ManualSnapshotResult(
            width=width,
            height=height,
            file_size_bytes=output_path.stat().st_size,
        )


@dataclass(frozen=True)
class LinuxXwdSnapshotResult:
    """Validated pixels captured from one explicit X11 client."""

    width: int
    height: int
    file_size_bytes: int
    xwd_sha256: str
    pixel_sha256: str
    pixel_format: str = "RGB24"
    pixel_bytes: bytes = field(repr=False, compare=False, default=b"")


class LinuxXwdWindowSnapshot:
    """Capture only a caller-supplied X11 client ID through xwd."""

    PROHIBITED_OPTIONS = frozenset({"-root", "-screen", "-name", "-frame"})

    def __init__(
        self,
        *,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._command_runner = command_runner or subprocess.run
        self._timeout = timeout

    @staticmethod
    def normalize_window_id(value: object) -> str:
        text = str(value or "").strip().lower()
        if not re.fullmatch(r"0x[0-9a-f]+", text):
            return ""
        numeric = int(text, 16)
        return hex(numeric) if numeric > 0 else ""

    @classmethod
    def build_command(
        cls, window_id: object, output_path: Path
    ) -> tuple[str, ...]:
        normalized = cls.normalize_window_id(window_id)
        if not normalized:
            raise ValueError("explicit non-zero hexadecimal window ID is required")
        if not output_path.is_absolute():
            raise ValueError("xwd output must use an absolute temporary path")
        command = (
            "xwd",
            "-silent",
            "-nobdrs",
            "-id",
            normalized,
            "-out",
            str(output_path),
        )
        if cls.PROHIBITED_OPTIONS.intersection(command) or "-id" not in command:
            raise ValueError("prohibited xwd fallback option")
        return command

    def capture(
        self,
        *,
        window_id: object,
        output_path: Path,
        expected_width: int,
        expected_height: int,
    ) -> LinuxXwdSnapshotResult:
        """Capture, validate and decode one XWD file without persisting its path."""
        command = self.build_command(window_id, output_path)
        if output_path.exists() or output_path.is_symlink():
            raise RuntimeError("temporary XWD output must not pre-exist")
        completed = self._command_runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout,
            shell=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"xwd failed with return code {completed.returncode}")
        metadata = output_path.lstat()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
        ):
            raise RuntimeError("xwd output is not a regular non-symlink file")
        descriptor = os.open(output_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino)
                != (metadata.st_dev, metadata.st_ino)
            ):
                raise RuntimeError("xwd output changed during secure open")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read()
        finally:
            os.close(descriptor)
        width, height, pixels = _decode_xwd_rgb24(
            data,
            expected_width=expected_width,
            expected_height=expected_height,
        )
        return LinuxXwdSnapshotResult(
            width=width,
            height=height,
            file_size_bytes=len(data),
            xwd_sha256=hashlib.sha256(data).hexdigest(),
            pixel_sha256=hashlib.sha256(pixels).hexdigest(),
            pixel_bytes=pixels,
        )


_XWD_HEADER_NAMES = (
    "header_size",
    "file_version",
    "pixmap_format",
    "pixmap_depth",
    "pixmap_width",
    "pixmap_height",
    "xoffset",
    "byte_order",
    "bitmap_unit",
    "bitmap_bit_order",
    "bitmap_pad",
    "bits_per_pixel",
    "bytes_per_line",
    "visual_class",
    "red_mask",
    "green_mask",
    "blue_mask",
    "bits_per_rgb",
    "colormap_entries",
    "ncolors",
    "window_width",
    "window_height",
    "window_x",
    "window_y",
    "window_bdrwidth",
)


def _mask_channel(pixel: int, mask: int) -> int:
    shift = (mask & -mask).bit_length() - 1
    maximum = mask >> shift
    return round(((pixel & mask) >> shift) * 255 / maximum)


def _decode_xwd_rgb24(
    data: bytes, *, expected_width: int, expected_height: int
) -> tuple[int, int, bytes]:
    if len(data) < 100:
        raise ValueError("XWD header is truncated")
    values = struct.unpack(">25I", data[:100])
    header = dict(zip(_XWD_HEADER_NAMES, values))
    if header["file_version"] != 7:
        little = dict(zip(_XWD_HEADER_NAMES, struct.unpack("<25I", data[:100])))
        if little["file_version"] == 7:
            raise ValueError("unsupported XWD header endianness")
        raise ValueError("unsupported XWD file version")
    if header["header_size"] < 100 or header["header_size"] > len(data):
        raise ValueError("contradictory XWD header size")
    if header["pixmap_format"] != 2:
        raise ValueError("unsupported XWD pixmap format")
    if header["bits_per_pixel"] not in {24, 32}:
        raise ValueError("unsupported XWD pixel format")
    if header["byte_order"] not in {0, 1}:
        raise ValueError("unsupported XWD pixel endianness")
    if header["bitmap_pad"] not in {8, 16, 32}:
        raise ValueError("unsupported XWD bitmap padding")
    width = int(header["pixmap_width"])
    height = int(header["pixmap_height"])
    if (
        width != expected_width
        or height != expected_height
        or header["window_width"] != expected_width
        or header["window_height"] != expected_height
    ):
        raise ValueError("XWD dimensions contradict authorized client geometry")
    bytes_per_pixel = header["bits_per_pixel"] // 8
    minimum_stride = width * bytes_per_pixel
    stride = int(header["bytes_per_line"])
    pad_bytes = header["bitmap_pad"] // 8
    if stride < minimum_stride or stride % pad_bytes != 0:
        raise ValueError("XWD stride contradicts dimensions or bitmap padding")
    masks = (
        int(header["red_mask"]),
        int(header["green_mask"]),
        int(header["blue_mask"]),
    )
    pixel_limit = (1 << header["bits_per_pixel"]) - 1
    if (
        any(mask <= 0 or mask > pixel_limit for mask in masks)
        or masks[0] & masks[1]
        or masks[0] & masks[2]
        or masks[1] & masks[2]
    ):
        raise ValueError("XWD RGB masks are absent, overlapping or out of range")
    pixel_offset = int(header["header_size"] + header["ncolors"] * 12)
    required_size = pixel_offset + stride * height
    if pixel_offset < 100 or required_size > len(data):
        raise ValueError("XWD pixel payload is truncated or contradictory")
    byte_order = "little" if header["byte_order"] == 0 else "big"
    pixels = bytearray(width * height * 3)
    target = 0
    for y in range(height):
        row = pixel_offset + y * stride
        for x in range(width):
            start = row + x * bytes_per_pixel
            raw = int.from_bytes(data[start : start + bytes_per_pixel], byte_order)
            pixels[target] = _mask_channel(raw, masks[0])
            pixels[target + 1] = _mask_channel(raw, masks[1])
            pixels[target + 2] = _mask_channel(raw, masks[2])
            target += 3
    return width, height, bytes(pixels)


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", ctypes.c_ushort),
        ("biBitCount", ctypes.c_ushort),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class _BitmapInfo(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BitmapInfoHeader),
        ("bmiColors", ctypes.c_uint32 * 1),
    ]


def _capture_windows_screen() -> tuple[int, int, bytes]:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    _configure_windows_api(user32, gdi32)

    left = int(user32.GetSystemMetrics(_SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(_SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(_SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(_SM_CYVIRTUALSCREEN))
    if width <= 0 or height <= 0:
        left = 0
        top = 0
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))

    screen_dc = user32.GetDC(None)
    if not screen_dc:
        raise RuntimeError("Unable to access the screen device context.")

    memory_dc = None
    bitmap = None
    previous_object = None
    try:
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        if not memory_dc:
            raise RuntimeError("Unable to create memory device context.")

        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        if not bitmap:
            raise RuntimeError("Unable to create screen bitmap.")

        previous_object = gdi32.SelectObject(memory_dc, bitmap)
        success = gdi32.BitBlt(
            memory_dc,
            0,
            0,
            width,
            height,
            screen_dc,
            left,
            top,
            _SRCCOPY,
        )
        if not success:
            raise RuntimeError("Unable to copy the screen into memory.")

        image_buffer = _read_bitmap_data(
            gdi32,
            memory_dc,
            bitmap,
            width,
            height,
        )
        return width, height, image_buffer
    finally:
        if previous_object:
            gdi32.SelectObject(memory_dc, previous_object)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)


def _read_bitmap_data(
    gdi32: ctypes.WinDLL,
    memory_dc: int,
    bitmap: int,
    width: int,
    height: int,
) -> bytes:
    bitmap_info = _BitmapInfo()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(_BitmapInfoHeader)
    bitmap_info.bmiHeader.biWidth = width
    bitmap_info.bmiHeader.biHeight = -height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = _BI_RGB

    buffer_size = width * height * 4
    bitmap_buffer = ctypes.create_string_buffer(buffer_size)
    scan_lines = gdi32.GetDIBits(
        memory_dc,
        bitmap,
        0,
        height,
        bitmap_buffer,
        ctypes.byref(bitmap_info),
        _DIB_RGB_COLORS,
    )
    if scan_lines != height:
        raise RuntimeError("Unable to read the captured bitmap.")

    return bytes(bitmap_buffer)


def _encode_png(
    width: int,
    height: int,
    image_buffer: bytes,
    compression: int,
) -> bytes:
    raw_rows = _build_png_rows(width, height, image_buffer)
    compression_level = max(0, min(9, int(compression)))

    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0),
            ),
            _png_chunk(b"IDAT", zlib.compress(raw_rows, compression_level)),
            _png_chunk(b"IEND", b""),
        ]
    )


def _build_png_rows(width: int, height: int, image_buffer: bytes) -> bytes:
    source_stride = width * 4
    target = bytearray((source_stride + 1) * height)
    target_index = 0

    for row_index in range(height):
        row_start = row_index * source_stride
        row_end = row_start + source_stride
        row = image_buffer[row_start:row_end]

        target[target_index] = 0
        target_index += 1
        for source_index in range(0, len(row), 4):
            target[target_index] = row[source_index + 2]
            target[target_index + 1] = row[source_index + 1]
            target[target_index + 2] = row[source_index]
            target[target_index + 3] = 255
            target_index += 4

    return bytes(target)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return b"".join(
        [
            struct.pack(">I", len(data)),
            chunk_type,
            data,
            struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF),
        ]
    )


def _configure_windows_api(user32: ctypes.WinDLL, gdi32: ctypes.WinDLL) -> None:
    user32.GetDC.argtypes = [ctypes.c_void_p]
    user32.GetDC.restype = ctypes.c_void_p
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.ReleaseDC.restype = ctypes.c_int

    gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
    gdi32.CreateCompatibleBitmap.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
    ]
    gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
    gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    gdi32.SelectObject.restype = ctypes.c_void_p
    gdi32.BitBlt.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint32,
    ]
    gdi32.BitBlt.restype = ctypes.c_int
    gdi32.GetDIBits.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.POINTER(_BitmapInfo),
        ctypes.c_uint,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    gdi32.DeleteObject.restype = ctypes.c_int
    gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
    gdi32.DeleteDC.restype = ctypes.c_int
