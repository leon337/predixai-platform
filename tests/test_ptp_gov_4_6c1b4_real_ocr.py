from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ptp_gov_4_6c1b4_validate_real_ocr.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_6c1b4", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WindowAuthorizationTests(unittest.TestCase):
    def snapshot(self, **overrides):
        values = {
            "window_id": "0x123",
            "pid": 100,
            "process_name": "chrome",
            "title_sha256": "a" * 64,
            "title_compatible": True,
            "left": 0,
            "top": 0,
            "width": 1366,
            "height": 768,
            "visible": True,
            "minimized": False,
            "foreground": True,
            "fallback_used": False,
        }
        values.update(overrides)
        return MODULE.WindowSnapshot(**values)

    def test_process_allowlist_is_exact(self):
        self.assertTrue(MODULE.process_allowlisted("chrome"))
        self.assertTrue(MODULE.process_allowlisted("firefox"))
        self.assertFalse(MODULE.process_allowlisted("code"))
        self.assertFalse(MODULE.process_allowlisted("terminal"))

    def test_title_requires_strong_combination(self):
        self.assertTrue(
            MODULE.title_compatible(
                "61.373 Caffeine Index - Google Chrome"
            )
        )
        self.assertTrue(
            MODULE.title_compatible(
                "SOLANA OTC - Olymp Trade - Google Chrome"
            )
        )
        self.assertFalse(MODULE.title_compatible("Caffeine Index"))
        self.assertFalse(MODULE.title_compatible("Index - Visual Studio Code"))

    def test_window_authorization_is_conjunctive(self):
        passed, failures = MODULE.window_authorized(self.snapshot())
        self.assertTrue(passed)
        self.assertEqual(failures, ())

        passed, failures = MODULE.window_authorized(
            self.snapshot(foreground=False)
        )
        self.assertFalse(passed)
        self.assertIn("FOREGROUND_FAIL", failures)

    def test_dynamic_title_price_does_not_break_identity(self):
        before = self.snapshot(title_sha256="a" * 64)
        after = self.snapshot(title_sha256="b" * 64)
        stable, failures = MODULE.window_stable(before, after)
        self.assertTrue(stable)
        self.assertEqual(failures, ())

    def test_pid_or_geometry_change_fails(self):
        before = self.snapshot()
        after = self.snapshot(pid=101, width=1200)
        stable, failures = MODULE.window_stable(before, after)
        self.assertFalse(stable)
        self.assertTrue(any("PID" in item for item in failures))
        self.assertTrue(any("WIDTH" in item for item in failures))


class PrivacyTests(unittest.TestCase):
    def test_private_result_redacts_raw_and_normalized_value(self):
        payload = MODULE.public_region_result(
            region_id="ACCOUNT_BALANCE",
            privacy_sensitive=True,
            passed=True,
            status="OCR_COMPLETED",
            pipeline_ready=True,
            confidence=95.0,
            language_used="por",
            normalization_valid=True,
            normalized_value="1234.56",
            variant="gray",
            reasons=(),
        )
        self.assertEqual(payload["normalized_value"], "REDACTED")
        self.assertNotIn("raw_text", payload)
        serialized = str(payload)
        self.assertNotIn("1234.56", serialized)

    def test_non_private_value_can_be_reported(self):
        payload = MODULE.public_region_result(
            region_id="PAYOUT",
            privacy_sensitive=False,
            passed=True,
            status="OCR_COMPLETED",
            pipeline_ready=True,
            confidence=90.0,
            language_used="por",
            normalization_valid=True,
            normalized_value="85%",
            variant="gray",
            reasons=(),
        )
        self.assertEqual(payload["normalized_value"], "85%")


class RegionContractTests(unittest.TestCase):
    def test_approved_tsv_has_exact_contract(self):
        path = ROOT / "reports" / "20260714_PTP-GOV.4.6C.1A_regioes_aprovadas.tsv"
        regions = MODULE.load_regions(path)
        self.assertEqual(len(regions), 9)
        self.assertEqual(
            {region.region_id for region in regions},
            MODULE.EXPECTED_OCR_REGION_IDS,
        )
        self.assertEqual(
            {region.region_id for region in regions if region.privacy_sensitive},
            MODULE.PRIVATE_REGION_IDS,
        )


if __name__ == "__main__":
    unittest.main()
