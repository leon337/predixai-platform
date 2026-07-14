from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

from predixai.live.live_market_reader import LiveMarketReader

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ptp_gov_4_6c1b3_validate_synthetic_ocr.py"

spec = importlib.util.spec_from_file_location(
    "ptp_gov_4_6c1b3_validator",
    SCRIPT,
)
if spec is None or spec.loader is None:
    raise RuntimeError("B3 validator could not be imported")
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


class B3ContractTests(unittest.TestCase):
    def test_region_set_reconciliation(self):
        result = validator.reconcile_primary_cases(
            validator.PRIMARY_CASES
        )
        self.assertEqual(result["ACTUAL_REGION_COUNT"], 9)
        self.assertEqual(result["DUPLICATE_REGION_COUNT"], 0)
        self.assertEqual(result["MISSING_REGION_COUNT"], 0)
        self.assertEqual(result["EXTRA_REGION_COUNT"], 0)

    def test_region_set_rejects_missing_and_duplicate(self):
        with self.assertRaises(validator.ValidationFailure):
            validator.reconcile_primary_cases(
                validator.PRIMARY_CASES[:-1]
            )
        with self.assertRaises(validator.ValidationFailure):
            validator.reconcile_primary_cases(
                validator.PRIMARY_CASES
                + (validator.PRIMARY_CASES[0],)
            )

    def test_recovery_preserves_legacy_reasons_and_known_payout_prefix(self):
        reader = LiveMarketReader()

        multiple_assets = reader.normalize_field(
            "ASSET",
            "SOLANA OTC EUR/USD OTC",
        )
        self.assertFalse(multiple_assets.valid)
        self.assertIn("MULTIPLE_ASSETS", multiple_assets.reasons)

        multiple_prices = reader.normalize_field(
            "PRICE",
            "61.373 59.617",
        )
        self.assertFalse(multiple_prices.valid)
        self.assertIn(
            "MULTIPLE_PRICE_VALUES",
            multiple_prices.reasons,
        )

        payout = reader.normalize_field("PAYOUT", "FT 90%")
        self.assertTrue(payout.valid)
        self.assertEqual(payout.normalized_text, "90%")

        contaminated_payout = reader.normalize_field(
            "PAYOUT",
            "erro 90% aviso",
        )
        self.assertFalse(contaminated_payout.valid)
        self.assertIn(
            "PAYOUT_CONTAMINATED",
            contaminated_payout.reasons,
        )

        tab_multiple = reader.normalize_field(
            "PRICE_SOURCE_BROWSER_TAB",
            "59.199 59.200",
        )
        self.assertFalse(tab_multiple.valid)
        self.assertIn(
            "TAB_MULTIPLE_PRICE_VALUES",
            tab_multiple.reasons,
        )

    def test_normalizer_negative_controls(self):
        with tempfile.TemporaryDirectory(prefix="b3-negative-") as temporary:
            result = validator.run_negative_controls(Path(temporary))
        self.assertEqual(
            result["negative_control_count"],
            result["negative_control_pass_count"],
        )

    @unittest.skipUnless(
        os.environ.get("PREDIXAI_RUN_REAL_OCR") == "1",
        "real OCR requires explicit executor flag",
    )
    def test_real_tesseract_smoke(self):
        result = validator.run_smoke_real_ocr()
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["tsv_call_count"], 0)


if __name__ == "__main__":
    unittest.main()
