from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import struct
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from predixai.capture.capture_engine import CaptureEngine
from predixai.capture.capture_snapshot import (
    LinuxXwdSnapshotResult,
    LinuxXwdWindowSnapshot,
)
from predixai.capture.snapshot_metadata import (
    AuthorizedWindowContract,
    WindowGeometry,
)
from predixai.capture.x11_display_topology import (
    X11DisplayTopology,
    derive_topology,
)
from predixai.live.broker_window_state import BrokerWindowState


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "runtime"
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_6b1a_reconcile_display_topology.py"


class FakeConfig:
    def resolve_project_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else ROOT / path


def observation(
    *,
    window_id="0xabc",
    pid=4242,
    process="synthetic-x11",
    title="AUTHORIZED SYNTHETIC WINDOW",
    geometry=(20, 30, 8, 6),
    visible=True,
    minimized=False,
    foreground=True,
):
    x, y, width, height = geometry
    return BrokerWindowState(
        title=title,
        resolution_width=width,
        resolution_height=height,
        left=x,
        top=y,
        maximized=False,
        foreground=foreground,
        detected_at="2026-07-13T00:00:00-03:00",
        metadata={
            "detected": True,
            "window_id": window_id,
            "window_pid": pid,
            "process_name": process,
            "window_visible": visible,
            "window_minimized": minimized,
            "fallback_used": False,
        },
    )


def contract():
    return AuthorizedWindowContract(
        window_id="0xabc",
        window_pid=4242,
        process_name="synthetic-x11",
        title_pattern=r"AUTHORIZED SYNTHETIC WINDOW",
        geometry=WindowGeometry(20, 30, 8, 6),
    )


def topology(marker="stable"):
    return X11DisplayTopology.from_values(
        {
            "TOPOLOGY_GATE_PASS": "YES",
            "LOGICAL_DESKTOP_COUNT": 1,
            "CAPTURE_SURFACE_COUNT": 1,
            "OUTPUT_LAYOUT_MODE": "MIRRORED_OR_CLONED",
            "MARKER": marker,
        }
    )


class FakeDetector:
    def __init__(self, states=None, error=None):
        self.states = list(states or [observation(), observation(), observation()])
        self.error = error
        self.calls = []

    def inspect_explicit_linux_window(self, window_id):
        self.calls.append(window_id)
        if self.error:
            raise self.error
        return self.states.pop(0)


class FakeTopologyInspector:
    def __init__(self, states=None):
        self.states = list(states or [topology(), topology()])

    def read_snapshot(self):
        return self.states.pop(0)


class FakeSnapshot:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def capture(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        kwargs["output_path"].write_bytes(b"temporary-xwd")
        pixels = bytes(range(8 * 6 * 3))
        return LinuxXwdSnapshotResult(
            width=8,
            height=6,
            file_size_bytes=13,
            xwd_sha256=hashlib.sha256(b"temporary-xwd").hexdigest(),
            pixel_sha256=hashlib.sha256(pixels).hexdigest(),
            pixel_bytes=pixels,
        )


def engine(*, detector=None, snapshot=None, topologies=None):
    return CaptureEngine(
        FakeConfig(),
        window_detector=detector or FakeDetector(),
        linux_snapshot=snapshot or FakeSnapshot(),
        topology_inspector=topologies or FakeTopologyInspector(),
    )


def xwd_bytes(width=8, height=6, **overrides):
    header = {
        "header_size": 100,
        "file_version": 7,
        "pixmap_format": 2,
        "pixmap_depth": 24,
        "pixmap_width": width,
        "pixmap_height": height,
        "xoffset": 0,
        "byte_order": 0,
        "bitmap_unit": 32,
        "bitmap_bit_order": 0,
        "bitmap_pad": 32,
        "bits_per_pixel": 32,
        "bytes_per_line": width * 4,
        "visual_class": 4,
        "red_mask": 0x00FF0000,
        "green_mask": 0x0000FF00,
        "blue_mask": 0x000000FF,
        "bits_per_rgb": 8,
        "colormap_entries": 256,
        "ncolors": 0,
        "window_width": width,
        "window_height": height,
        "window_x": 0,
        "window_y": 0,
        "window_bdrwidth": 0,
    }
    header.update(overrides)
    names = (
        "header_size", "file_version", "pixmap_format", "pixmap_depth",
        "pixmap_width", "pixmap_height", "xoffset", "byte_order",
        "bitmap_unit", "bitmap_bit_order", "bitmap_pad", "bits_per_pixel",
        "bytes_per_line", "visual_class", "red_mask", "green_mask", "blue_mask",
        "bits_per_rgb", "colormap_entries", "ncolors", "window_width",
        "window_height", "window_x", "window_y", "window_bdrwidth",
    )
    packed = struct.pack(">25I", *(header[name] for name in names))
    name_padding = b"\0" * max(0, header["header_size"] - 100)
    stride = max(0, header["bytes_per_line"])
    payload = bytearray(stride * max(0, header["pixmap_height"]))
    for y in range(min(height, header["pixmap_height"])):
        for x in range(width):
            start = y * stride + x * 4
            if start + 4 <= len(payload):
                value = ((x * 31) % 256) << 16 | ((y * 43) % 256) << 8 | 17
                payload[start:start + 4] = value.to_bytes(4, "little")
    return packed + name_padding + bytes(payload)


def writing_runner(data, *, returncode=0, mode="file"):
    def run(command, **kwargs):
        del kwargs
        output = Path(command[command.index("-out") + 1])
        if mode == "file":
            output.write_bytes(data)
        elif mode == "symlink":
            target = output.parent / "target.xwd"
            target.write_bytes(data)
            output.symlink_to(target)
        elif mode == "directory":
            output.mkdir()
        return subprocess.CompletedProcess(command, returncode, "", "controlled")
    return run


def hash_tree(path):
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"MISSING")
        return digest.hexdigest()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


class PtpGov46B2AuthorizedCaptureTests(unittest.TestCase):
    def test_valid_capture_uses_explicit_client_window_id(self):
        captured = engine().capture_authorized_linux_window(contract())
        self.assertTrue(captured.capture_published)
        self.assertEqual((captured.width, captured.height), (8, 6))
        self.assertIsNotNone(captured.pixel_bytes)

    def test_nonexistent_window_id_fails_before_xwd(self):
        backend = FakeSnapshot()
        captured = engine(
            detector=FakeDetector(error=RuntimeError("missing")), snapshot=backend
        ).capture_authorized_linux_window(contract())
        self.assertFalse(captured.capture_published)
        self.assertFalse(captured.xwd_executed)
        self.assertEqual(backend.calls, [])

    def test_pid_mismatch_fails_closed(self):
        states = [observation(pid=9), observation(pid=9)]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("AUTHORIZED_WINDOW_PID_MISMATCH", captured.reasons)

    def test_process_name_mismatch_fails_closed(self):
        states = [observation(process="other"), observation(process="other")]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("AUTHORIZED_PROCESS_NAME_MISMATCH", captured.reasons)

    def test_title_mismatch_fails_closed(self):
        states = [observation(title="OTHER"), observation(title="OTHER")]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("AUTHORIZED_TITLE_MISMATCH", captured.reasons)

    def test_geometry_mismatch_fails_closed(self):
        states = [observation(geometry=(20, 30, 9, 6)), observation(geometry=(20, 30, 9, 6))]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("AUTHORIZED_GEOMETRY_MISMATCH", captured.reasons)

    def test_minimized_window_fails_closed(self):
        states = [observation(minimized=True), observation(minimized=True)]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("WINDOW_MINIMIZED", captured.reasons)

    def test_missing_required_foreground_fails_closed(self):
        states = [observation(foreground=False), observation(foreground=False)]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertIn("WINDOW_NOT_FOREGROUND", captured.reasons)

    def test_geometry_change_after_xwd_discards_capture(self):
        states = [observation(), observation(), observation(geometry=(21, 30, 8, 6))]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertTrue(captured.xwd_executed)
        self.assertFalse(captured.capture_published)
        self.assertIsNone(captured.pixel_bytes)

    def test_topology_change_after_xwd_discards_capture(self):
        captured = engine(
            topologies=FakeTopologyInspector([topology("before"), topology("after")])
        ).capture_authorized_linux_window(contract())
        self.assertIn("POSTCHECK_TOPOLOGY_CHANGED", captured.reasons)
        self.assertIsNone(captured.pixel_bytes)

    def test_fullscreen_desktop_and_active_window_fallbacks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "capture.xwd"
            command = LinuxXwdWindowSnapshot.build_command("0xabc", output)
            self.assertEqual(command[:5], ("xwd", "-silent", "-nobdrs", "-id", "0xabc"))
            for value in (None, "", "0", "active", "-root", "-screen", "-name", "-frame"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    LinuxXwdWindowSnapshot.build_command(value, output)

    def test_temporary_capture_directory_is_completely_removed(self):
        backend = FakeSnapshot()
        captured = engine(snapshot=backend).capture_authorized_linux_window(contract())
        parent = backend.calls[0]["output_path"].parent
        self.assertFalse(parent.exists())
        self.assertEqual(captured.temporary_file_count_final, 0)
        self.assertTrue(captured.temporary_directory_removed)

    def test_failed_capture_never_publishes_image_bytes(self):
        states = [observation(), observation(), observation(title="CHANGED")]
        captured = engine(detector=FakeDetector(states)).capture_authorized_linux_window(contract())
        self.assertFalse(captured.capture_allowed)
        self.assertEqual(captured.to_dict()["PIXEL_BYTES_RETURNED"], "NO")

    def test_data_runtime_tree_remains_unchanged(self):
        before = hash_tree(RUNTIME)
        engine().capture_authorized_linux_window(contract())
        self.assertEqual(hash_tree(RUNTIME), before)

    def test_xwd_child_process_is_reaped_without_residual_process(self):
        backend = FakeSnapshot()
        engine(snapshot=backend).capture_authorized_linux_window(contract())
        self.assertEqual(len(backend.calls), 1)
        self.assertFalse(backend.calls[0]["output_path"].parent.exists())

    def test_xwd_nonzero_return_code_fails_closed(self):
        backend = LinuxXwdWindowSnapshot(command_runner=writing_runner(b"", returncode=9))
        captured = engine(snapshot=backend).capture_authorized_linux_window(contract())
        self.assertFalse(captured.capture_published)
        self.assertTrue(captured.xwd_executed)

    def test_xwd_timeout_fails_closed(self):
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        backend = LinuxXwdWindowSnapshot(command_runner=timeout)
        captured = engine(snapshot=backend).capture_authorized_linux_window(contract())
        self.assertIn("CAPTURE_ERROR:TimeoutExpired", captured.reasons)

    def test_truncated_xwd_header_is_rejected(self):
        backend = LinuxXwdWindowSnapshot(command_runner=writing_runner(b"short"))
        captured = engine(snapshot=backend).capture_authorized_linux_window(contract())
        self.assertFalse(captured.capture_published)

    def test_unsupported_xwd_endianness_or_pixel_format_is_rejected(self):
        for data in (xwd_bytes(byte_order=2), xwd_bytes(bits_per_pixel=16)):
            with self.subTest(), self.assertRaises(ValueError):
                backend = LinuxXwdWindowSnapshot(command_runner=writing_runner(data))
                with tempfile.TemporaryDirectory() as temporary:
                    backend.capture(
                        window_id="0xabc",
                        output_path=Path(temporary) / "capture.xwd",
                        expected_width=8,
                        expected_height=6,
                    )

    def test_xwd_stride_masks_or_dimensions_contradiction_is_rejected(self):
        variants = (
            xwd_bytes(bytes_per_line=4),
            xwd_bytes(green_mask=0x00FF0000),
            xwd_bytes(window_width=9),
        )
        for data in variants:
            with self.subTest(), self.assertRaises(ValueError):
                backend = LinuxXwdWindowSnapshot(command_runner=writing_runner(data))
                with tempfile.TemporaryDirectory() as temporary:
                    backend.capture(
                        window_id="0xabc",
                        output_path=Path(temporary) / "capture.xwd",
                        expected_width=8,
                        expected_height=6,
                    )

    def test_missing_symlink_or_nonregular_xwd_output_is_rejected(self):
        cases = (("missing", None), ("symlink", "symlink"), ("directory", "directory"))
        for label, mode in cases:
            with self.subTest(label=label), self.assertRaises((OSError, RuntimeError)):
                runner = (
                    (lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
                    if mode is None
                    else writing_runner(xwd_bytes(), mode=mode)
                )
                backend = LinuxXwdWindowSnapshot(command_runner=runner)
                with tempfile.TemporaryDirectory() as temporary:
                    backend.capture(
                        window_id="0xabc",
                        output_path=Path(temporary) / "capture.xwd",
                        expected_width=8,
                        expected_height=6,
                    )

    def test_missing_required_contract_field_fails_closed(self):
        mapping = {
            "AUTHORIZED_WINDOW_ID": "0xabc",
            "AUTHORIZED_WINDOW_PID": 4242,
            "AUTHORIZED_PROCESS_NAME": "synthetic-x11",
            "AUTHORIZED_GEOMETRY": {"x": 20, "y": 30, "width": 8, "height": 6},
        }
        captured = engine().capture_authorized_linux_window(mapping)
        self.assertIn("CONTRACT_INVALID:ValueError", captured.reasons)

    def test_pixel_bytes_are_absent_from_repr_and_serialization(self):
        captured = engine().capture_authorized_linux_window(contract())
        self.assertNotIn("pixel_bytes", repr(captured))
        serialized = repr(captured.to_dict())
        self.assertNotIn(repr(captured.pixel_bytes), serialized)
        self.assertNotIn("temporary-xwd", serialized)

    def test_topology_has_single_functional_source_of_truth(self):
        spec = importlib.util.spec_from_file_location("topology_validator", VALIDATOR_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        validator_source = VALIDATOR_PATH.read_text(encoding="utf-8")
        functional_source = inspect.getsource(__import__(
            "predixai.capture.x11_display_topology", fromlist=["*"]
        ))
        self.assertIs(module.derive_topology, derive_topology)
        self.assertNotIn("def derive_topology(", validator_source)
        self.assertNotIn("def parse_query(", validator_source)
        self.assertNotIn("scripts.", functional_source)


if __name__ == "__main__":
    unittest.main()
