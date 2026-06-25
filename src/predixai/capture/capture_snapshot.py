"""Manual screen snapshot writer for the Capture Engine."""

from __future__ import annotations

import ctypes
import platform
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

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
