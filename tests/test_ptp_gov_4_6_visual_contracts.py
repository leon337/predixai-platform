from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_6a_characterize_visual_contracts.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_6a_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o validador da PTP-GOV.4.6A")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def matching_contract():
    return VALIDATOR.build_example_contract()


def matching_observation():
    return VALIDATOR.build_example_observation()


def synthetic_png(width: int = 8, height: int = 6) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    return VALIDATOR.PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class PtpGov46AVisualContractTests(unittest.TestCase):
    def test_matching_explicit_window_contract_allows_future_capture_only(self) -> None:
        result = VALIDATOR.evaluate_capture_gate(matching_contract(), matching_observation())
        self.assertEqual(result["CAPTURE_ALLOWED"], "YES")
        self.assertEqual(result["CAPTURE_EXECUTED"], "NO")
        self.assertEqual(result["OCR_EXECUTED"], "NO")
        self.assertEqual(result["SOURCE_STATE"], "SOURCE_CONFIRMED")

    def test_each_required_contract_field_fails_closed_when_missing(self) -> None:
        for field in VALIDATOR.AUTHORIZED_WINDOW_CONTRACT_FIELDS:
            with self.subTest(field=field):
                contract = matching_contract()
                contract.pop(field)
                result = VALIDATOR.evaluate_capture_gate(contract, matching_observation())
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertIn(f"CONTRACT_FIELD_MISSING:{field}", result["REASONS"])

    def test_identity_pid_process_title_and_geometry_mismatch_fail_closed(self) -> None:
        mutations = {
            "OBSERVED_WINDOW_ID": "0x4200002",
            "OBSERVED_WINDOW_PID": 9999,
            "OBSERVED_PROCESS_NAME": "untrusted-browser",
            "OBSERVED_TITLE": "Página genérica",
            "OBSERVED_GEOMETRY": {"x": 1, "y": 0, "width": 1366, "height": 768},
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                observation = matching_observation()
                observation[field] = value
                result = VALIDATOR.evaluate_capture_gate(matching_contract(), observation)
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertEqual(result["INVALID_READING_PUBLISHED"], "NO")
                self.assertEqual(result["LAST_VALID_READING_PRESERVED"], "YES")

    def test_visibility_minimized_foreground_and_stability_fail_closed(self) -> None:
        mutations = {
            "WINDOW_VISIBLE": False,
            "WINDOW_MINIMIZED": True,
            "WINDOW_FOREGROUND": False,
            "GEOMETRY_STABLE": False,
            "SOURCE_CONFIRMED": False,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                observation = matching_observation()
                observation[field] = value
                result = VALIDATOR.evaluate_capture_gate(matching_contract(), observation)
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertEqual(result["SOURCE_STATE"], "WAITING_SOURCE_OR_SOURCE_NOT_CONFIRMED")

    def test_single_monitor_is_mandatory(self) -> None:
        observation = matching_observation()
        observation["MONITOR_COUNT"] = 2
        result = VALIDATOR.evaluate_capture_gate(matching_contract(), observation)
        self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
        self.assertIn("SINGLE_MONITOR_CONTRACT_VIOLATED", result["REASONS"])

    def test_full_screen_or_generic_active_window_fallback_is_prohibited(self) -> None:
        for mode in ("FULL_SCREEN", "ACTIVE_WINDOW_GENERIC", "DESKTOP"):
            with self.subTest(mode=mode):
                observation = matching_observation()
                observation["CAPTURE_TARGET_MODE"] = mode
                result = VALIDATOR.evaluate_capture_gate(matching_contract(), observation)
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertIn("EXPLICIT_WINDOW_TARGET_REQUIRED", result["REASONS"])

    def test_vscode_codex_and_terminal_processes_are_never_authorized(self) -> None:
        for process in ("code", "codex", "xfce4-terminal", "bash"):
            with self.subTest(process=process):
                contract = matching_contract()
                observation = matching_observation()
                contract["AUTHORIZED_PROCESS_NAME"] = process
                observation["OBSERVED_PROCESS_NAME"] = process
                result = VALIDATOR.evaluate_capture_gate(contract, observation)
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertIn("AUTHORIZED_PROCESS_PROHIBITED", result["REASONS"])

    def test_vscode_codex_and_terminal_titles_are_rejected(self) -> None:
        for title in ("Visual Studio Code", "Codex", "Terminal"):
            with self.subTest(title=title):
                contract = matching_contract()
                observation = matching_observation()
                contract["AUTHORIZED_TITLE_PATTERN"] = re_escape(title)
                observation["OBSERVED_TITLE"] = title
                result = VALIDATOR.evaluate_capture_gate(contract, observation)
                self.assertEqual(result["CAPTURE_ALLOWED"], "NO")
                self.assertIn("OBSERVED_TITLE_PROHIBITED", result["REASONS"])

    def test_browser_requires_exact_authorized_pid_process_and_title(self) -> None:
        contract = matching_contract()
        observation = matching_observation()
        contract["AUTHORIZED_PROCESS_NAME"] = "firefox"
        contract["AUTHORIZED_TITLE_PATTERN"] = r"Broker Simulado - [A-Z ]+"
        observation["OBSERVED_PROCESS_NAME"] = "firefox"
        self.assertEqual(
            VALIDATOR.evaluate_capture_gate(contract, observation)["CAPTURE_ALLOWED"],
            "YES",
        )
        observation["OBSERVED_WINDOW_PID"] += 1
        self.assertEqual(
            VALIDATOR.evaluate_capture_gate(contract, observation)["CAPTURE_ALLOWED"],
            "NO",
        )

    def test_x11_preflight_characterizes_tools_without_capture_commands(self) -> None:
        calls = []

        def fake_run(command):
            calls.append(tuple(command))
            return {"available": True, "returncode": 0, "stdout": "ok", "stderr": ""}

        result = VALIDATOR.characterize_environment(
            environ={"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0.0"},
            which=lambda name: f"/usr/bin/{name}" if name in {"wmctrl", "xprop", "xwininfo", "xwd"} else None,
            command_runner=fake_run,
        )
        self.assertEqual(result["DISPLAY_SERVER"], "X11")
        self.assertEqual(result["WINDOW_METADATA_CAPABILITY"], "PASS_METADATA_ONLY_NOT_SOURCE_AUTHORIZATION")
        self.assertEqual(result["DIRECT_WINDOW_CAPTURE_CAPABILITY"], "AVAILABLE_NOT_EXECUTED_XWD_EXPLICIT_WINDOW_ID")
        self.assertEqual(result["CAPTURE_EXECUTED"], "NO")
        self.assertEqual(tuple(calls), VALIDATOR.ALLOWED_METADATA_COMMANDS)
        self.assertTrue(all(command[0] not in VALIDATOR.PROHIBITED_EXECUTABLES for command in calls))

    def test_wayland_without_explicit_backend_fails_closed(self) -> None:
        result = VALIDATOR.characterize_environment(
            environ={"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
            which=lambda name: None,
            command_runner=lambda command: self.fail(f"unexpected command: {command}"),
        )
        self.assertEqual(result["DISPLAY_SERVER"], "WAYLAND")
        self.assertEqual(result["WINDOW_METADATA_CAPABILITY"], "BLOCKED_METADATA_TOOLCHAIN")
        self.assertEqual(result["DIRECT_WINDOW_CAPTURE_CAPABILITY"], "BLOCKED_NO_CONFIRMED_EXPLICIT_WINDOW_BACKEND")
        self.assertEqual(result["FULL_SCREEN_FALLBACK"], "PROHIBITED")

    def test_metadata_runner_rejects_capture_ocr_and_unlisted_commands(self) -> None:
        for command in (("xwd", "-id", "0x1"), ("tesseract", "image.png", "stdout"), ("wmctrl", "-l")):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "not allowlisted"):
                    VALIDATOR._safe_metadata_run(command)

    def test_synthetic_png_is_validated_without_capture_or_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "synthetic.png"
            image.write_bytes(synthetic_png())
            result = VALIDATOR.validate_synthetic_png(image)
        self.assertEqual(result["SYNTHETIC_IMAGE_VALID"], "YES")
        self.assertEqual((result["WIDTH"], result["HEIGHT"]), (8, 6))
        self.assertEqual(result["CAPTURE_EXECUTED"], "NO")
        self.assertEqual(result["OCR_EXECUTED"], "NO")

    def test_invalid_synthetic_image_is_rejected_without_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "invalid.png"
            image.write_bytes(b"not-a-real-image")
            result = VALIDATOR.validate_synthetic_png(image)
        self.assertEqual(result["SYNTHETIC_IMAGE_VALID"], "NO")
        self.assertEqual(result["CAPTURE_EXECUTED"], "NO")
        self.assertEqual(result["OCR_EXECUTED"], "NO")


def re_escape(value: str) -> str:
    import re

    return re.escape(value)


if __name__ == "__main__":
    unittest.main()
