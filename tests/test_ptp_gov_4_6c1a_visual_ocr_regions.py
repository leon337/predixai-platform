from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from predixai.live.field_locator import (
    AUTHORIZED_VISUAL_REGION_BY_ID,
    AUTHORIZED_VISUAL_REGION_SPECS,
    FieldLocator,
)
from predixai.live.live_market_reader import LiveMarketReader
from predixai.live.broker_window_state import BrokerWindowState
from predixai.vision.roi import RegionOfInterest, RelativeRegionGeometry
from predixai.vision.roi_crop_engine import ROICropEngine


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/ptp_gov_4_6c1a_calibrate_broker_regions.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_6c1a", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("C.1A validator could not be loaded")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def roi(identifier="BROKER_PRICE", x=1, y=1, width=2, height=2):
    stamp = datetime.now().astimezone().isoformat()
    return RegionOfInterest(
        id=identifier,
        name=identifier,
        description="test",
        x=x,
        y=y,
        width=width,
        height=height,
        enabled=True,
        created_at=stamp,
        updated_at=stamp,
    )


def broker_state(title="61.373 Solana OTC", process="brave", foreground=True):
    return BrokerWindowState(
        title=title,
        resolution_width=1000,
        resolution_height=700,
        left=0,
        top=0,
        maximized=True,
        foreground=foreground,
        detected_at="2026-07-13T00:00:00-03:00",
        metadata={
            "detected": True,
            "window_id": "0xabc",
            "window_pid": 1234,
            "process_name": process,
            "window_visible": True,
            "window_minimized": False,
        },
    )


def valid_boxes():
    boxes = {
        "ASSET": (600, 350, 90, 40),
        "PAYOUT": (610, 360, 30, 15),
        "CHART_AREA": (0, 0, 300, 300),
        "TIMEFRAME": (10, 240, 40, 20),
        "ORDER_NOTIFICATION_POPUP": (350, 0, 300, 300),
        "ORDER_MODE_BY_PRICE": (370, 30, 70, 30),
        "ORDER_MODE_BY_TIME": (460, 30, 70, 30),
        "PROFITABILITY_FILTER": (370, 80, 160, 30),
        "OPENING_TIME": (370, 130, 160, 30),
        "SAVE_ORDER_BUTTON": (370, 190, 160, 40),
    }
    remaining = [
        specification.region_id
        for specification in AUTHORIZED_VISUAL_REGION_SPECS
        if specification.region_id not in boxes
    ]
    for index, region_id in enumerate(remaining):
        boxes[region_id] = (index % 5 * 120, 350 + index // 5 * 70, 90, 40)
    return boxes


class RelativeRegionTests(unittest.TestCase):
    def test_relative_geometry_round_trips_manual_pixels(self):
        value = RelativeRegionGeometry.from_pixels(
            x=100, y=70, width=250, height=80, window_width=1000, window_height=700
        )
        self.assertEqual(value.to_pixels(window_width=1000, window_height=700), (100, 70, 250, 80))

    def test_relative_geometry_rejects_negative_origin(self):
        with self.assertRaises(ValueError):
            RelativeRegionGeometry(-0.1, 0.0, 0.2, 0.2)

    def test_relative_geometry_rejects_nonpositive_dimensions(self):
        with self.assertRaises(ValueError):
            RelativeRegionGeometry(0.1, 0.1, 0.0, 0.2)

    def test_relative_geometry_rejects_out_of_bounds_without_clamp(self):
        with self.assertRaises(ValueError):
            RelativeRegionGeometry(0.9, 0.1, 0.2, 0.2)

    def test_manual_pixel_geometry_rejects_out_of_bounds(self):
        with self.assertRaises(ValueError):
            RelativeRegionGeometry.from_pixels(
                x=90, y=0, width=20, height=10, window_width=100, window_height=100
            )


class RGB24CropTests(unittest.TestCase):
    def setUp(self):
        self.width = 4
        self.height = 4
        self.pixels = bytes(range(self.width * self.height * 3))
        self.engine = ROICropEngine()

    def test_rgb24_crop_extracts_exact_rows(self):
        crop = self.engine.crop_rgb24(
            roi=roi(), pixel_bytes=self.pixels, image_width=self.width, image_height=self.height
        )
        expected = self.pixels[15:21] + self.pixels[27:33]
        self.assertEqual(crop.pixel_bytes, expected)
        self.assertEqual(crop.sha256, hashlib.sha256(expected).hexdigest())

    def test_rgb24_crop_rejects_contradictory_source_size(self):
        with self.assertRaises(ValueError):
            self.engine.crop_rgb24(
                roi=roi(), pixel_bytes=b"short", image_width=self.width, image_height=self.height
            )

    def test_rgb24_crop_rejects_out_of_bounds_without_clamp(self):
        with self.assertRaises(ValueError):
            self.engine.crop_rgb24(
                roi=roi(x=3, y=3, width=2, height=2),
                pixel_bytes=self.pixels,
                image_width=self.width,
                image_height=self.height,
            )

    def test_pixel_bytes_are_absent_from_repr_and_serialization(self):
        crop = self.engine.crop_rgb24(
            roi=roi(), pixel_bytes=self.pixels, image_width=self.width, image_height=self.height
        )
        self.assertNotIn(str(crop.pixel_bytes), repr(crop))
        self.assertNotIn("pixel_bytes", json.dumps(crop.to_dict()).lower())

    def test_preprocessed_png_is_deterministic(self):
        crop = self.engine.crop_rgb24(
            roi=roi(), pixel_bytes=self.pixels, image_width=self.width, image_height=self.height
        )
        first = self.engine.preprocess_png(crop, scale=3, threshold=150)
        second = self.engine.preprocess_png(crop, scale=3, threshold=150)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_preprocessing_rejects_invalid_threshold(self):
        crop = self.engine.crop_rgb24(
            roi=roi(), pixel_bytes=self.pixels, image_width=self.width, image_height=self.height
        )
        with self.assertRaises(ValueError):
            self.engine.preprocess_png(crop, threshold=300)


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.reader = LiveMarketReader()

    def test_asset_preserves_otc_and_normalizes_spaces(self):
        result = self.reader.normalize_field("ASSET", "  Solana    OTC ")
        self.assertTrue(result.valid)
        self.assertEqual(result.normalized_text, "SOLANA OTC")

    def test_multiple_assets_are_rejected(self):
        result = self.reader.normalize_field("ASSET", "SOLANA OTC EUR/USD OTC")
        self.assertFalse(result.valid)
        self.assertIn("MULTIPLE_ASSETS", result.reasons)

    def test_price_accepts_dot_or_comma_without_inventing_digits(self):
        for raw, expected in (("61.373", "61.373"), ("61,373", "61.373"), ("61373", "61373")):
            with self.subTest(raw=raw):
                result = self.reader.normalize_field("PRICE", raw)
                self.assertTrue(result.valid)
                self.assertEqual(result.normalized_text, expected)

    def test_multiple_price_values_are_rejected(self):
        result = self.reader.normalize_field("PRICE", "61.373 59.617")
        self.assertFalse(result.valid)
        self.assertIn("MULTIPLE_PRICE_VALUES", result.reasons)

    def test_payout_requires_percent_and_range(self):
        self.assertEqual(self.reader.normalize_field("PAYOUT", "FT 90%").normalized_text, "90%")
        self.assertFalse(self.reader.normalize_field("PAYOUT", "90").valid)
        self.assertFalse(self.reader.normalize_field("PAYOUT", "101%").valid)

    def test_price_source_browser_tab_requires_exact_price_and_asset(self):
        result = self.reader.normalize_field("PRICE_SOURCE_BROWSER_TAB", "59.199 Solana")
        self.assertTrue(result.valid)
        self.assertEqual(result.normalized_text, "59.199|SOLANA")
        self.assertFalse(
            self.reader.normalize_field("PRICE_SOURCE_BROWSER_TAB", "59.199 59.200 Solana").valid
        )

    def test_countdown_is_dynamic_and_temporally_validated(self):
        self.assertTrue(self.reader.normalize_field("COUNTDOWN", "00:05").valid)
        self.assertTrue(self.reader.validate_countdown_sequence(("00:05", "00:04", "00:03")).valid)
        self.assertTrue(self.reader.validate_countdown_sequence(("00:01", "00:00", "00:59")).valid)
        self.assertFalse(self.reader.validate_countdown_sequence(("00:05", "00:05", "00:04")).valid)

    def test_timeframe_is_separate_from_chart_area(self):
        self.assertEqual(self.reader.normalize_field("TIMEFRAME", "5m").normalized_text, "5m")
        self.assertFalse(self.reader.normalize_field("TIMEFRAME", "chart").valid)

    def test_system_clock_replaces_broker_time_region(self):
        with self.assertRaises(ValueError):
            self.reader.normalize_field("BROKER_TIME", "18:15")
        self.assertTrue(self.reader.normalize_field("OPENING_TIME", "22:00").valid)


class CalibrationContractTests(unittest.TestCase):
    def test_contract_requires_complete_23_region_map(self):
        geometries = {
            region_id: VALIDATOR.RelativeRegionGeometry.from_pixels(
                x=box[0], y=box[1], width=box[2], height=box[3], window_width=700, window_height=600
            ).to_dict().values()
            for region_id, box in valid_boxes().items()
        }
        geometries = {region_id: tuple(values) for region_id, values in geometries.items()}
        result = FieldLocator().build_authorized_region_contracts(geometries)
        self.assertEqual(len(result.definitions), 23)
        self.assertTrue(all(item.required for item in result.definitions))
        self.assertNotIn("FULL_SCREEN", {item.region_id for item in result.definitions})
        self.assertNotIn("BROKER_TIME", {item.region_id for item in result.definitions})
        self.assertEqual(result.metadata["time_source"], "SYSTEM_CLOCK")

    def test_contract_rejects_missing_authorized_region(self):
        with self.assertRaises(ValueError):
            FieldLocator().build_authorized_region_contracts({"ASSET": (0.1, 0.1, 0.1, 0.1)})

    def test_visual_map_has_no_prohibited_area_and_exact_classifications(self):
        self.assertEqual(len(AUTHORIZED_VISUAL_REGION_SPECS), 23)
        self.assertEqual(len(AUTHORIZED_VISUAL_REGION_BY_ID), 23)
        self.assertTrue(all(specification.classifications for specification in AUTHORIZED_VISUAL_REGION_SPECS))
        self.assertNotIn("PROHIBITED_AREA", {
            classification
            for specification in AUTHORIZED_VISUAL_REGION_SPECS
            for classification in specification.classifications
        })

    def test_price_source_is_active_browser_tab_not_chart_label(self):
        specification = AUTHORIZED_VISUAL_REGION_BY_ID["PRICE_SOURCE_BROWSER_TAB"]
        self.assertEqual(specification.source, "ACTIVE_BROWSER_TAB_VISUAL_TITLE")
        self.assertNotIn("INDEX", specification.normalization_rule)
        self.assertNotIn("GRAPH", specification.source)

    def test_popup_has_closed_open_contract_and_five_open_only_children(self):
        children = tuple(
            specification.region_id
            for specification in AUTHORIZED_VISUAL_REGION_SPECS
            if specification.parent_region_id == "ORDER_NOTIFICATION_POPUP"
        )
        self.assertEqual(
            children,
            (
                "ORDER_MODE_BY_PRICE",
                "ORDER_MODE_BY_TIME",
                "PROFITABILITY_FILTER",
                "OPENING_TIME",
                "SAVE_ORDER_BUTTON",
            ),
        )
        self.assertTrue(all(AUTHORIZED_VISUAL_REGION_BY_ID[item].visibility_state == "POPUP_OPEN" for item in children))

    def test_region_overlap_is_detected(self):
        self.assertTrue(VALIDATOR.boxes_overlap((0, 0, 10, 10), (5, 5, 10, 10)))
        self.assertFalse(VALIDATOR.boxes_overlap((0, 0, 10, 10), (10, 0, 10, 10)))

    def test_complete_manual_boxes_allow_only_documented_parent_child_overlap(self):
        VALIDATOR.validate_boxes(valid_boxes(), 700, 600)
        invalid = valid_boxes()
        invalid["ENTRY_VALUE"] = invalid["DURATION"]
        with self.assertRaisesRegex(ValueError, "unauthorized region overlap"):
            VALIDATOR.validate_boxes(invalid, 700, 600)

    def test_build_proposals_reconciles_23_rows(self):
        boxes = valid_boxes()
        pixels = bytes((index % 256 for index in range(700 * 600 * 3)))
        proposals = VALIDATOR.build_region_proposals(
            boxes=boxes, pixel_bytes=pixels, width=700, height=600
        )
        self.assertEqual(len(proposals), 23)
        self.assertEqual(tuple(item.field_id for item in proposals), tuple(item.region_id for item in AUTHORIZED_VISUAL_REGION_SPECS))
        self.assertTrue(all(item.ocr_text == "NOT_EXECUTED" for item in proposals))

    def test_ocr_and_visual_state_regions_are_reconciled(self):
        self.assertEqual(sum(item.requires_ocr for item in AUTHORIZED_VISUAL_REGION_SPECS), 11)
        self.assertEqual(sum(not item.requires_ocr for item in AUTHORIZED_VISUAL_REGION_SPECS), 12)


class PreflightAndPrivacyTests(unittest.TestCase):
    def test_capture_countdown_precedes_candidate_enrollment(self):
        emitted = []
        sleeps = []
        VALIDATOR.run_capture_countdown(
            3,
            sleeper=sleeps.append,
            emit=emitted.append,
        )
        self.assertEqual(emitted[0], "CONTAGEM INICIADA — ABRA A CORRETORA AGORA")
        self.assertEqual(
            emitted[1:],
            [
                "CAPTURA_EM_SEGUNDOS=3",
                "CAPTURA_EM_SEGUNDOS=2",
                "CAPTURA_EM_SEGUNDOS=1",
                "CONTAGEM_CONCLUIDA=YES",
            ],
        )
        self.assertEqual(sleeps, [1.0, 1.0, 1.0])

    def test_volatile_quote_is_excluded_from_stable_broker_title_signature(self):
        pattern = VALIDATOR.stable_broker_title_pattern("▼ 61.373 Solana OTC")
        self.assertRegex("▼ 61.421 Solana OTC", pattern)
        self.assertNotRegex("Visual Studio Code", pattern)

    def test_title_adapter_validates_raw_title_before_canonical_hashing(self):
        delegate = unittest.mock.Mock()
        delegate.inspect_explicit_linux_window.return_value = broker_state()
        adapter = VALIDATOR.StableAuthorizedTitleDetector(
            delegate,
            VALIDATOR.stable_broker_title_pattern("61.373 Solana OTC"),
        )
        observed = adapter.inspect_explicit_linux_window("0xabc")
        self.assertEqual(observed.title, VALIDATOR.STABLE_AUTHORIZED_TITLE)
        delegate.inspect_explicit_linux_window.return_value = broker_state(title="Visual Studio Code")
        self.assertEqual(
            adapter.inspect_explicit_linux_window("0xabc").title,
            "Visual Studio Code",
        )

    def test_tesseract_absence_pauses_only_real_ocr(self):
        with patch.object(VALIDATOR.shutil, "which", return_value=None):
            metadata = VALIDATOR.tesseract_metadata()
        self.assertEqual(metadata["TESSERACT_AVAILABLE"], "NO")
        self.assertEqual(metadata["OCR_REAL_ALLOWED"], "NO")
        self.assertEqual(metadata["OCR_STATUS"], "PAUSED_DEPENDENCY_MISSING")

    def test_broker_candidate_accepts_user_foreground_otc_window(self):
        allowed, reason = VALIDATOR.candidate_allowed(broker_state())
        self.assertTrue(allowed)
        self.assertEqual(reason, "AUTHORIZED_CANDIDATE")

    def test_technical_or_unrelated_browser_candidate_is_rejected(self):
        for state in (
            broker_state(title="Visual Studio Code — predixai", process="code"),
            broker_state(title="YouTube", process="brave"),
            broker_state(title="61.373 Solana OTC", process="brave", foreground=False),
        ):
            with self.subTest(title=state.title):
                self.assertFalse(VALIDATOR.candidate_allowed(state)[0])

    def test_default_profile_remains_full_screen_until_leo_confirms(self):
        profile = json.loads((ROOT / "config/screen_profiles/default_screen_profile.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in profile["regions"]], ["FULL_SCREEN"])

    def test_ocr_is_not_attempted_when_dependency_is_missing(self):
        proposal = VALIDATOR.RegionProposal(
            field_id="ASSET",
            region_id="BROKER_ASSET",
            x=0,
            y=0,
            width=4,
            height=4,
            window_width=4,
            window_height=4,
            x_ratio=0.0,
            y_ratio=0.0,
            width_ratio=1.0,
            height_ratio=1.0,
            crop_sha256="0" * 64,
        )
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.execute_ocr_if_allowed(
                (proposal,),
                boxes={"BROKER_ASSET": (0, 0, 4, 4)},
                pixel_bytes=bytes(4 * 4 * 3),
                width=4,
                height=4,
                temporary_root=Path(temporary),
                metadata={"OCR_REAL_ALLOWED": "NO"},
            )
        self.assertIsNot(result[0], proposal)
        self.assertEqual(result[0].field_id, proposal.field_id)
        self.assertEqual(result[0].region_id, proposal.region_id)
        self.assertEqual(result[0].ocr_text, "NOT_EXECUTED")
        self.assertEqual(result[0].ocr_confidence, 0.0)
        self.assertEqual(
            result[0].calibration_status,
            "VISUAL_STATE_REGION_CALIBRATED",
        )


if __name__ == "__main__":
    unittest.main()
