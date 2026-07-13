from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_6b1_characterize_x11_window_capture.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_6b1_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o validador da PTP-GOV.4.6B.1")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def make_xwd(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    name = b"synthetic\x00"
    header_size = 100 + len(name)
    bytes_per_line = width * 4
    values = (
        header_size, 7, 2, 24, width, height, 0, 0, 32, 0, 32, 32,
        bytes_per_line, 4, 0x00FF0000, 0x0000FF00, 0x000000FF, 8, 256, 0,
        width, height, 0, 0, 0,
    )
    payload = bytearray()
    for red, green, blue in pixels:
        payload.extend(bytes((blue, green, red, 0)))
    path.write_bytes(struct.pack(">25I", *values) + name + bytes(payload))


def quadrant_pixels(width: int = 20, height: int = 20) -> list[tuple[int, int, int]]:
    result = []
    for y in range(height):
        for x in range(width):
            index = (2 if y >= height // 2 else 0) + (1 if x >= width // 2 else 0)
            result.append(VALIDATOR.AUTHORIZED_COLORS[index])
    return result


def authorized_snapshot(*, foreground: bool = True) -> dict:
    geometry = {"x": 80, "y": 90, "width": 620, "height": 420}
    window = {
        "WINDOW_ID": "0x410001",
        "WINDOW_PID": 12345,
        "PROCESS_NAME": "python3",
        "WINDOW_TITLE": VALIDATOR.AUTHORIZED_TITLE,
        "GEOMETRY": geometry,
        "WINDOW_VISIBLE": True,
        "WINDOW_MINIMIZED": False,
        "WINDOW_FOREGROUND": foreground,
        "ACTIVE_WINDOW_ID": "0x410001" if foreground else "0x410002",
        "STACKING_ORDER": ("0x410001", "0x410002"),
        "FRAME_EXTENTS": (1, 1, 24, 1),
        "WM_CLASS": ("ptp", "Ptp"),
    }
    overlay = {
        **window,
        "WINDOW_ID": "0x410002",
        "WINDOW_PID": 12346,
        "WINDOW_TITLE": VALIDATOR.OVERLAY_TITLE,
        "GEOMETRY": {"x": 900, "y": 90, "width": 300, "height": 220},
        "WINDOW_VISIBLE": False,
        "WINDOW_FOREGROUND": not foreground,
    }
    return {
        "AUTHORIZED_WINDOW_ID": window["WINDOW_ID"],
        "OVERLAY_WINDOW_ID": overlay["WINDOW_ID"],
        "ACTIVE_WINDOW_ID": window["ACTIVE_WINDOW_ID"],
        "STACKING_ORDER": window["STACKING_ORDER"],
        "AUTHORIZED_GEOMETRY": geometry,
        "OVERLAY_GEOMETRY": overlay["GEOMETRY"],
        "AUTHORIZED": window,
        "OVERLAY": overlay,
    }


class PtpGov46B1X11CaptureCharacterizationTests(unittest.TestCase):
    def test_xwd_command_targets_only_explicit_client_window_without_frame(self) -> None:
        command = VALIDATOR.build_xwd_command("0x410001", Path("/tmp/capture.xwd"))
        self.assertEqual(command, ("xwd", "-silent", "-nobdrs", "-id", "0x410001", "-out", "/tmp/capture.xwd"))
        self.assertNotIn("-frame", command)
        self.assertFalse(VALIDATOR.PROHIBITED_XWD_OPTIONS.intersection(command))

    def test_xwd_command_rejects_missing_or_invalid_window_id(self) -> None:
        for value in (None, "", "active", "0x0", -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                VALIDATOR.build_xwd_command(value, Path("/tmp/capture.xwd"))

    def test_full_screen_active_window_and_desktop_fallbacks_are_rejected(self) -> None:
        for mode in ("FULL_SCREEN", "ACTIVE_WINDOW_GENERIC", "DESKTOP"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                VALIDATOR.reject_fallback_mode(mode)

    def test_metadata_commands_are_allowlisted_and_targeted(self) -> None:
        with self.assertRaises(ValueError):
            VALIDATOR.run_metadata_command(("wmctrl", "-l"))
        with self.assertRaises(ValueError):
            VALIDATOR.run_metadata_command(("xprop", "-root", "_NET_WM_NAME"))

    def test_root_metadata_parser_records_active_and_stacking_ids_only(self) -> None:
        parsed = VALIDATOR.parse_root_metadata(
            "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x410002\n"
            "_NET_CLIENT_LIST_STACKING(WINDOW): window id # 0x410001, 0x410002\n"
        )
        self.assertEqual(parsed["ACTIVE_WINDOW_ID"], "0x410002")
        self.assertEqual(parsed["STACKING_ORDER"], ("0x410001", "0x410002"))

    def test_targeted_xprop_parser_records_pid_title_class_state_and_extents(self) -> None:
        parsed = VALIDATOR.parse_xprop_window(
            '_NET_WM_PID(CARDINAL) = 12345\nWM_CLASS(STRING) = "ptp", "Ptp"\n'
            f'_NET_WM_NAME(UTF8_STRING) = "{VALIDATOR.AUTHORIZED_TITLE}"\n'
            "_NET_WM_STATE(ATOM) = _NET_WM_STATE_HIDDEN\n"
            "_NET_FRAME_EXTENTS(CARDINAL) = 1, 1, 24, 1\n"
        )
        self.assertEqual(parsed["WINDOW_PID"], 12345)
        self.assertEqual(parsed["WINDOW_TITLE"], VALIDATOR.AUTHORIZED_TITLE)
        self.assertTrue(parsed["WINDOW_MINIMIZED"])
        self.assertEqual(parsed["FRAME_EXTENTS"], (1, 1, 24, 1))

    def test_xwininfo_parser_records_geometry_visibility(self) -> None:
        parsed = VALIDATOR.parse_xwininfo(
            "Absolute upper-left X:  80\nAbsolute upper-left Y:  90\n"
            "Width: 620\nHeight: 420\nMap State: IsViewable\n"
        )
        self.assertEqual(parsed["GEOMETRY"], {"x": 80, "y": 90, "width": 620, "height": 420})
        self.assertTrue(parsed["WINDOW_VISIBLE"])

    def test_geometry_intersection_and_stacking_order_are_deterministic(self) -> None:
        first = {"x": 0, "y": 0, "width": 100, "height": 100}
        partial = {"x": 50, "y": 50, "width": 100, "height": 100}
        away = {"x": 100, "y": 0, "width": 50, "height": 50}
        self.assertTrue(VALIDATOR.geometry_intersects(first, partial))
        self.assertFalse(VALIDATOR.geometry_intersects(first, away))
        self.assertTrue(VALIDATOR.is_above("0x1", "0x2", ("0x1", "0x2")))

    def test_xwd_parser_and_authorized_quadrant_signature_are_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.xwd"
            make_xwd(path, 20, 20, quadrant_pixels())
            result = VALIDATOR.analyze_xwd(
                VALIDATOR.parse_xwd(path), {"x": 0, "y": 0, "width": 20, "height": 20}
            )
        self.assertEqual(result["BACKEND_TECHNICAL_CAPTURE_RESULT"], "ISOLATED_PIXELS_CONFIRMED")
        self.assertEqual(result["AUTHORIZED_SIGNATURE_COMPLETE"], "YES")
        self.assertEqual(result["OVERLAY_SIGNATURE_PRESENT"], "NO")
        self.assertEqual(result["EXTERNAL_PIXEL_SIGNATURE_PRESENT"], "NO")

    def test_overlay_magenta_signature_blocks_pixel_isolation(self) -> None:
        pixels = quadrant_pixels()
        pixels[0:20] = [VALIDATOR.OVERLAY_COLOR] * 20
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "overlay.xwd"
            make_xwd(path, 20, 20, pixels)
            result = VALIDATOR.analyze_xwd(
                VALIDATOR.parse_xwd(path), {"x": 0, "y": 0, "width": 20, "height": 20}
            )
        self.assertEqual(result["OVERLAY_SIGNATURE_PRESENT"], "YES")
        self.assertEqual(result["BACKEND_TECHNICAL_CAPTURE_RESULT"], "PIXEL_ISOLATION_NOT_CONFIRMED")

    def test_external_pixel_signature_blocks_pixel_isolation(self) -> None:
        pixels = quadrant_pixels()
        pixels[0:20] = [(12, 34, 56)] * 20
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "external.xwd"
            make_xwd(path, 20, 20, pixels)
            result = VALIDATOR.analyze_xwd(
                VALIDATOR.parse_xwd(path), {"x": 0, "y": 0, "width": 20, "height": 20}
            )
        self.assertEqual(result["EXTERNAL_PIXEL_SIGNATURE_PRESENT"], "YES")
        self.assertEqual(result["BACKEND_TECHNICAL_CAPTURE_RESULT"], "PIXEL_ISOLATION_NOT_CONFIRMED")

    def test_operational_gate_and_backend_result_remain_separate(self) -> None:
        snapshot = authorized_snapshot(foreground=False)
        contract = VALIDATOR.build_contract({**snapshot["AUTHORIZED"], "WINDOW_FOREGROUND": True})
        operational, gate = VALIDATOR.classify_operational_gate(contract, snapshot, monitor_count=1)
        backend = {"BACKEND_TECHNICAL_CAPTURE_RESULT": "ISOLATED_PIXELS_CONFIRMED"}
        self.assertEqual(operational, "BLOCKED_WINDOW_NOT_FOREGROUND")
        self.assertEqual(gate["CAPTURE_ALLOWED"], "NO")
        self.assertEqual(backend["BACKEND_TECHNICAL_CAPTURE_RESULT"], "ISOLATED_PIXELS_CONFIRMED")

    def test_overlay_above_authorized_window_blocks_operational_gate(self) -> None:
        snapshot = authorized_snapshot(foreground=False)
        snapshot["OVERLAY"]["WINDOW_VISIBLE"] = True
        snapshot["OVERLAY"]["GEOMETRY"] = {"x": 100, "y": 100, "width": 200, "height": 200}
        snapshot["OVERLAY_GEOMETRY"] = snapshot["OVERLAY"]["GEOMETRY"]
        contract = VALIDATOR.build_contract({**snapshot["AUTHORIZED"], "WINDOW_FOREGROUND": True})
        operational, gate = VALIDATOR.classify_operational_gate(contract, snapshot, monitor_count=1)
        self.assertEqual(operational, "BLOCKED_OVERLAY_ABOVE_AUTHORIZED")
        self.assertIn("OVERLAY_ABOVE_AUTHORIZED_WINDOW", gate["REASONS"])

    def test_synthetic_override_is_private_and_absent_from_application(self) -> None:
        self.assertTrue(VALIDATOR.SYNTHETIC_CHARACTERIZATION_OVERRIDE)
        self.assertFalse(VALIDATOR.FUNCTIONAL_CAPTURE_OVERRIDE)
        application_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (ROOT / "src" / "predixai").rglob("*.py")
        )
        self.assertNotIn("SYNTHETIC_CHARACTERIZATION_OVERRIDE", application_text)
        self.assertNotIn("FUNCTIONAL_CAPTURE_OVERRIDE", application_text)

    def test_synthetic_capture_rejects_non_owned_window_id_before_xwd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(PermissionError):
                VALIDATOR.synthetic_characterization_capture(
                    "0x410099",
                    owned_window_ids={"0x410001"},
                    temporary_root=Path(temporary),
                    expected_geometry={"x": 0, "y": 0, "width": 20, "height": 20},
                    frame_extents=(),
                )


if __name__ == "__main__":
    unittest.main()
