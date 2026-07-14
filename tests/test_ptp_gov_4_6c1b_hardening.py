from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from predixai.live.field_locator import AUTHORIZED_VISUAL_REGION_SPECS, FieldLocator
from predixai.live.live_market_reader import FieldNormalizationResult, LiveMarketReader
from predixai.ocr.ocr_cache import OCRCache
from predixai.ocr.ocr_engine import OCREngine
from predixai.ocr.ocr_result_validator import OCRResultValidator
from predixai.ocr.providers.base_provider import OCRProviderExecution, OCRProviderStatus
from predixai.ocr.providers.tesseract_provider import TesseractOCRProvider


def png_file(root: Path) -> Path:
    path = root / "input.png"
    path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91Jpz"
            "AAAAFklEQVR4nGP8//8/AwMDEwMDAwMDAwAkBgMB/DXemwAAAABJRU5ErkJggg=="
        )
    )
    return path


def ready_status() -> OCRProviderStatus:
    return OCRProviderStatus("tesseract", True, True, True, "tesseract 5.3.4", "por", True, True)


def missing_status() -> OCRProviderStatus:
    return OCRProviderStatus("tesseract", False, False, False, "not_detected", "", False, False)


def completed() -> OCRProviderExecution:
    return OCRProviderExecution("OCR_COMPLETED", True, "ABC", 95.0, "por", "")


class ProviderTests(unittest.TestCase):
    def test_missing_binary_is_not_ready(self):
        provider = TesseractOCRProvider(); provider.binary_path = None
        status = provider.load()
        self.assertFalse(status.ready); self.assertFalse(status.text_extraction_enabled)

    def test_language_selection_is_fail_closed(self):
        provider = TesseractOCRProvider(language="por", fallback_language="eng")
        self.assertEqual(provider._select_language(("por", "eng")), "por")
        self.assertEqual(provider._select_language(("eng",)), "eng")
        self.assertEqual(provider._select_language(("spa",)), "")

    def test_oserror_becomes_ocr_error(self):
        provider = TesseractOCRProvider(); provider.binary_path = "/usr/bin/tesseract"
        with patch.object(provider, "_detect_languages", return_value=("por",)):
            with patch("predixai.ocr.providers.tesseract_provider.subprocess.run", side_effect=PermissionError("blocked")):
                result = provider.execute("/tmp/input.png")
        self.assertEqual(result.status, "OCR_ERROR"); self.assertIn("PermissionError", result.error)

    def test_invalid_confidence_words_are_excluded(self):
        provider = TesseractOCRProvider()
        tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t90\tVALID\n5\t1\t1\t1\t1\t2\t0\t0\t1\t1\tbad\tINVALID\n5\t1\t1\t1\t1\t3\t0\t0\t1\t1\t-1\tNEGATIVE\n"
        text, confidence = provider._parse_tsv_output(tsv)
        self.assertEqual(text, "VALID"); self.assertEqual(confidence, 90.0)


class EngineAndCacheTests(unittest.TestCase):
    def test_unready_and_disabled_provider_are_not_executed(self):
        for status, enabled, expected in ((missing_status(), True, "OCR_ERROR"), (ready_status(), False, "OCR_DISABLED")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                image = png_file(Path(temporary))
                with patch.object(TesseractOCRProvider, "load", return_value=status):
                    with patch.object(TesseractOCRProvider, "execute", side_effect=AssertionError("must not execute")):
                        result = OCREngine({"provider":"tesseract","text_extraction_enabled":enabled}).prepare_pipeline(image)
                self.assertEqual(result.status, expected); self.assertFalse(result.pipeline_ready)

    def test_low_confidence_is_invalid(self):
        checked = OCRResultValidator(80).validate(ready_status(), OCRProviderExecution("OCR_COMPLETED", True, "ABC", 20, "por", ""), "por", "eng")
        self.assertFalse(checked.valid); self.assertFalse(checked.confidence_valid)

    def test_cache_key_changes_and_corruption_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); image = png_file(root); cache = OCRCache(root / "cache")
            self.assertNotEqual(cache.compute_key(image, namespace={"psm":6}), cache.compute_key(image, namespace={"psm":7}))
            (root / "cache").mkdir(); key = "a" * 64; (root / "cache" / f"{key}.json").write_text("{broken", encoding="utf-8")
            self.assertIsNone(cache.load(key))

    def test_private_and_error_results_are_not_cached(self):
        cases = ((True, completed()), (False, OCRProviderExecution("OCR_ERROR", False, "", 0.0, "por", "failed")))
        for privacy, execution in cases:
            with self.subTest(privacy=privacy), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); image = png_file(root); cache_dir = root / "cache"
                with patch.object(TesseractOCRProvider, "load", return_value=ready_status()):
                    with patch.object(TesseractOCRProvider, "execute", return_value=execution):
                        OCREngine({"provider":"tesseract","language":"por","fallback_language":"eng","text_extraction_enabled":True,"min_confidence":80,"cache_enabled":True,"cache_directory":str(cache_dir),"privacy_sensitive":privacy}).prepare_pipeline(image)
                self.assertFalse(cache_dir.exists())


class NormalizationTests(unittest.TestCase):
    def setUp(self): self.reader = LiveMarketReader()

    def test_negative_and_brl_values(self):
        negative = self.reader.normalize_field("PROFIT_DISPLAY", "R$ -10,00")
        balance = self.reader.normalize_field("ACCOUNT_BALANCE", "R$ 1.234,56")
        self.assertEqual(negative.normalized_text, "-10.00"); self.assertEqual(balance.normalized_text, "1234.56")

    def test_account_type_ambiguity_and_redaction(self):
        demo = self.reader.normalize_field("ACCOUNT_TYPE", "Conta Demo")
        ambiguous = self.reader.normalize_field("ACCOUNT_TYPE", "Conta Demo Conta Real")
        self.assertEqual(demo.normalized_text, "DEMO"); self.assertFalse(ambiguous.valid)
        payload = FieldNormalizationResult("ACCOUNT_BALANCE", "R$ 100,00", "100.00", True).to_dict(redact_raw_text=True)
        self.assertEqual(payload["RAW_TEXT"], "REDACTED_LOCAL_VALUE")

    def test_regions_are_independent(self):
        geometries = {spec.region_id: (0.0, 0.0, 0.01, 0.01) for spec in AUTHORIZED_VISUAL_REGION_SPECS}
        mapping = FieldLocator().build_authorized_region_contracts(geometries)
        self.assertTrue(mapping.metadata["independent_regions"]); self.assertFalse(mapping.metadata["hierarchical_regions"])


if __name__ == "__main__": unittest.main()
