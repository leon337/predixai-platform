#!/usr/bin/env python3
"""PTP-GOV.4.6C.1B.3 — deterministic offline synthetic OCR validation."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy
import PIL
from PIL import Image, ImageDraw, ImageFont, features

from predixai.live.live_market_reader import LiveMarketReader
from predixai.ocr.ocr_engine import OCREngine
from predixai.ocr.ocr_result import OCRResult
from predixai.ocr.ocr_validator import OCRValidator
from predixai.ocr.providers import tesseract_provider as provider_module
from predixai.ocr.providers.tesseract_provider import TesseractOCRProvider
from predixai.vision.roi import RegionOfInterest
from predixai.vision.roi_crop import RGB24Crop
from predixai.vision.roi_crop_engine import ROICropEngine

PTP_ID = "PTP-GOV.4.6C.1B.3-R1"
EXPECTED_REGION_IDS = frozenset(
    {
        "ASSET",
        "PAYOUT",
        "PRICE_SOURCE_BROWSER_TAB",
        "TIMEFRAME",
        "ENTRY_VALUE",
        "DURATION",
        "PROFIT_DISPLAY",
        "ACCOUNT_BALANCE",
        "ACCOUNT_TYPE",
    }
)
PRIVATE_REGION_IDS = frozenset({"ACCOUNT_BALANCE", "ACCOUNT_TYPE"})
VARIANTS = (
    ("gray", None),
    ("threshold_110", 110),
    ("threshold_150", 150),
    ("threshold_190", 190),
)


@dataclass(frozen=True)
class SyntheticCase:
    region_id: str
    source_text: str
    expected: str
    privacy_sensitive: bool = False


PRIMARY_CASES = (
    SyntheticCase("ASSET", "SOLANA OTC", "SOLANA OTC"),
    SyntheticCase("PAYOUT", "85%", "85%"),
    SyntheticCase(
        "PRICE_SOURCE_BROWSER_TAB",
        "61.373",
        "61.373",
    ),
    SyntheticCase("TIMEFRAME", "1m", "1m"),
    SyntheticCase("ENTRY_VALUE", "R$ 10,00", "10.00"),
    SyntheticCase("DURATION", "1 min", "1m"),
    SyntheticCase("PROFIT_DISPLAY", "R$ 8,50", "8.50"),
    SyntheticCase(
        "ACCOUNT_BALANCE",
        "R$ 1.234,56",
        "1234.56",
        True,
    ),
    SyntheticCase("ACCOUNT_TYPE", "Conta Demo", "DEMO", True),
)

POSITIVE_EXTRA_CASES = (
    SyntheticCase("ASSET", "EUR/USD OTC", "EUR/USD OTC"),
    SyntheticCase("PROFIT_DISPLAY", "R$ -10,00", "-10.00"),
    SyntheticCase("PROFIT_DISPLAY", "R$ −10,00", "-10.00"),
)

NEGATIVE_TEXT_CASES = (
    ("ACCOUNT_BALANCE", "R$ 1.234"),
    ("TIMEFRAME", "9999d"),
    ("DURATION", "0m"),
    ("PAYOUT", "erro 85% aviso"),
    ("TIMEFRAME", "abc 1m xyz"),
    ("ENTRY_VALUE", "antigo R$ 10,00"),
)


class ValidationFailure(RuntimeError):
    pass


@dataclass
class TesseractTrace:
    tsv_calls: list[tuple[str, ...]]

    @property
    def count(self) -> int:
        return len(self.tsv_calls)


@contextlib.contextmanager
def trace_tesseract_tsv_calls() -> Iterator[TesseractTrace]:
    original_run = provider_module.subprocess.run
    trace = TesseractTrace(tsv_calls=[])

    def wrapped_run(command, *args, **kwargs):
        command_tuple = tuple(str(item) for item in command)
        if (
            command_tuple
            and Path(command_tuple[0]).name == "tesseract"
            and command_tuple[-1:] == ("tsv",)
        ):
            trace.tsv_calls.append(command_tuple)
        return original_run(command, *args, **kwargs)

    provider_module.subprocess.run = wrapped_run
    try:
        yield trace
    finally:
        provider_module.subprocess.run = original_run


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_output(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return "NOT_AVAILABLE"
    return (completed.stdout or "").strip()


def package_version(package: str) -> str:
    result = command_output(
        ["dpkg-query", "-W", "-f=${Version}", package]
    )
    return result if result else "NOT_AVAILABLE"


def locate_font() -> Path:
    candidates = (
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSansMono-Bold.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Bold.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/liberation/"
            "LiberationSans-Bold.ttf"
        ),
    )
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            font = ImageFont.truetype(str(path), size=64)
            for text in (
                "R$ −10,00",
                "EUR/USD OTC",
                "Conta Demo",
            ):
                mask = font.getmask(text)
                if mask.getbbox() is None:
                    raise ValueError("font cannot render required text")
        except (OSError, ValueError):
            continue
        return path
    raise ValidationFailure("DETERMINISTIC_TRUETYPE_FONT_NOT_FOUND")


def locate_numeric_font() -> Path:
    candidates = (
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSansMono-Bold.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/freefont/"
            "FreeSansBold.ttf"
        ),
    )
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            try:
                ImageFont.truetype(str(path), size=64)
            except OSError:
                continue
            return path
    raise ValidationFailure("DETERMINISTIC_NUMERIC_FONT_NOT_FOUND")


def render_text_rgb(
    text: str,
    font_path: Path,
) -> Image.Image:
    font = ImageFont.truetype(str(font_path), size=64)
    scratch = Image.new("RGB", (1, 1), "white")
    draw = ImageDraw.Draw(scratch)
    left, top, right, bottom = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=0,
    )
    padding_x = 36
    padding_y = 28
    width = max(320, right - left + padding_x * 2)
    height = max(120, bottom - top + padding_y * 2)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    x = padding_x - left
    y = padding_y - top
    draw.text(
        (x, y),
        text,
        font=font,
        fill="black",
        stroke_width=0,
    )
    return image


def image_to_crop(
    image: Image.Image,
    *,
    region_id: str,
) -> RGB24Crop:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixel_bytes = rgb.tobytes()
    roi = RegionOfInterest(
        id=region_id,
        name=region_id,
        description="Synthetic deterministic OCR corpus",
        x=0,
        y=0,
        width=width,
        height=height,
        enabled=True,
        created_at="2000-01-01T00:00:00+00:00",
        updated_at="2000-01-01T00:00:00+00:00",
    )
    return ROICropEngine().crop_rgb24(
        roi=roi,
        pixel_bytes=pixel_bytes,
        image_width=width,
        image_height=height,
    )


def strict_result_accepted(
    result: OCRResult,
    *,
    normalized_valid: bool,
    normalized_text: str,
    expected: str,
    require_cold: bool,
) -> bool:
    if require_cold and result.cache_hit:
        return False
    return (
        result.status == "OCR_COMPLETED"
        and result.pipeline_ready
        and result.provider_ready
        and result.text_extracted
        and result.confidence_valid
        and result.language_valid
        and not result.validation_errors
        and normalized_valid
        and normalized_text == expected
    )


def base_config(
    cache_directory: Path,
    *,
    cache_enabled: bool,
    privacy_sensitive: bool,
    language: str = "por",
    fallback_language: str = "eng",
) -> dict[str, object]:
    return {
        "provider": "tesseract",
        "language": language,
        "fallback_language": fallback_language,
        "text_extraction_enabled": True,
        "min_confidence": 80.0,
        "cache_enabled": cache_enabled,
        "cache_directory": str(cache_directory),
        "benchmark_enabled": False,
        "psm": 7,
        "timeout_seconds": 8,
        "privacy_sensitive": privacy_sensitive,
    }


def reconcile_primary_cases(
    cases: tuple[SyntheticCase, ...],
) -> dict[str, int | str]:
    ids = [case.region_id for case in cases]
    actual = set(ids)
    duplicates = len(ids) - len(actual)
    missing = EXPECTED_REGION_IDS - actual
    extra = actual - EXPECTED_REGION_IDS
    private_actual = {
        case.region_id
        for case in cases
        if case.privacy_sensitive
    }
    if (
        duplicates
        or missing
        or extra
        or private_actual != PRIVATE_REGION_IDS
    ):
        raise ValidationFailure(
            "CORPUS_REGION_RECONCILIATION_FAILED:"
            f"duplicates={duplicates}:"
            f"missing={sorted(missing)}:"
            f"extra={sorted(extra)}:"
            f"private={sorted(private_actual)}"
        )
    return {
        "EXPECTED_REGION_COUNT": len(EXPECTED_REGION_IDS),
        "ACTUAL_REGION_COUNT": len(actual),
        "DUPLICATE_REGION_COUNT": duplicates,
        "MISSING_REGION_COUNT": len(missing),
        "EXTRA_REGION_COUNT": len(extra),
        "PRIVATE_REGION_RECONCILIATION": "PASS",
    }


def write_verified_png(path: Path, png_bytes: bytes) -> None:
    path.write_bytes(png_bytes)
    validation = OCRValidator().validate(path)
    if not validation.valid:
        raise ValidationFailure(
            "SYNTHETIC_PNG_VALIDATION_FAILED:"
            + "|".join(validation.errors)
        )
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if image.size[0] <= 0 or image.size[1] <= 0:
            raise ValidationFailure(
                "SYNTHETIC_PNG_DIMENSIONS_INVALID"
            )


def run_case_variants(
    case: SyntheticCase,
    *,
    root: Path,
    font_path: Path,
    numeric_font_path: Path,
) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    selected_font = (
        numeric_font_path
        if case.region_id == "PRICE_SOURCE_BROWSER_TAB"
        else font_path
    )
    image = render_text_rgb(case.source_text, selected_font)
    crop = image_to_crop(image, region_id=case.region_id)
    variant_hashes: dict[str, str] = {}
    accepted: list[dict[str, object]] = []
    normalized_values: set[str] = set()

    with trace_tesseract_tsv_calls() as trace:
        for variant_name, threshold in VARIANTS:
            png_bytes = ROICropEngine.preprocess_png(
                crop,
                scale=3,
                threshold=threshold,
            )
            png_sha = sha256_bytes(png_bytes)
            if png_sha in variant_hashes.values():
                continue
            variant_hashes[variant_name] = png_sha
            png_path = root / (
                f"{case.region_id}-{variant_name}.png"
            )
            write_verified_png(png_path, png_bytes)
            result = OCREngine(
                base_config(
                    root / "cache-disabled",
                    cache_enabled=False,
                    privacy_sensitive=case.privacy_sensitive,
                )
            ).prepare_pipeline(png_path)
            normalized = LiveMarketReader().normalize_field(
                case.region_id,
                result.text,
            )
            if strict_result_accepted(
                result,
                normalized_valid=normalized.valid,
                normalized_text=normalized.normalized_text,
                expected=case.expected,
                require_cold=True,
            ):
                accepted.append(
                    {
                        "variant": variant_name,
                        "confidence": result.confidence,
                        "language": result.language_used,
                        "image_sha256": result.image_sha256,
                    }
                )
                normalized_values.add(
                    normalized.normalized_text
                )

    if len(variant_hashes) < 2:
        raise ValidationFailure(
            f"UNIQUE_VARIANT_COUNT_TOO_LOW:{case.region_id}"
        )
    if len(accepted) < 2:
        raise ValidationFailure(
            f"VALID_VARIANT_COUNT_TOO_LOW:{case.region_id}:"
            f"{len(accepted)}"
        )
    if normalized_values != {case.expected}:
        raise ValidationFailure(
            f"VARIANT_NORMALIZED_CONFLICT:{case.region_id}:"
            f"{sorted(normalized_values)}"
        )
    if trace.count < len(variant_hashes):
        raise ValidationFailure(
            f"TESSERACT_CALL_COUNT_TOO_LOW:{case.region_id}:"
            f"{trace.count}:{len(variant_hashes)}"
        )
    for command in trace.tsv_calls:
        if "--psm" not in command or "7" not in command:
            raise ValidationFailure("TESSERACT_PSM_7_NOT_USED")
        if "-l" not in command or "por" not in command:
            raise ValidationFailure(
                "TESSERACT_PORTUGUESE_NOT_USED"
            )

    return {
        "region_id": case.region_id,
        "source_rgb_sha256": crop.sha256,
        "variant_hashes": variant_hashes,
        "unique_variant_count": len(variant_hashes),
        "valid_variant_count": len(accepted),
        "normalized": (
            "REDACTED_SYNTHETIC_PRIVATE"
            if case.privacy_sensitive
            else case.expected
        ),
        "best_confidence": max(
            float(item["confidence"]) for item in accepted
        ),
        "real_tesseract_tsv_call_count": trace.count,
        "privacy_sensitive": case.privacy_sensitive,
    }


def run_cold_round(
    round_root: Path,
    font_path: Path,
    numeric_font_path: Path,
) -> dict[str, object]:
    round_root.mkdir(parents=True, exist_ok=True)
    results = [
        run_case_variants(
            case,
            root=round_root / case.region_id,
            font_path=font_path,
            numeric_font_path=numeric_font_path,
        )
        for case in PRIMARY_CASES
    ]
    return {
        "regions": {
            str(item["region_id"]): item
            for item in results
        },
        "pass_count": len(results),
        "tsv_call_count": sum(
            int(item["real_tesseract_tsv_call_count"])
            for item in results
        ),
    }


def compare_cold_rounds(
    first: dict[str, object],
    second: dict[str, object],
) -> None:
    first_regions = first["regions"]
    second_regions = second["regions"]
    if set(first_regions) != set(second_regions):
        raise ValidationFailure(
            "COLD_ROUND_REGION_SET_MISMATCH"
        )
    for region_id in first_regions:
        left = first_regions[region_id]
        right = second_regions[region_id]
        if left["source_rgb_sha256"] != right["source_rgb_sha256"]:
            raise ValidationFailure(
                f"COLD_ROUND_RGB_HASH_MISMATCH:{region_id}"
            )
        if left["variant_hashes"] != right["variant_hashes"]:
            raise ValidationFailure(
                f"COLD_ROUND_VARIANT_HASH_MISMATCH:{region_id}"
            )
        if left["normalized"] != right["normalized"]:
            raise ValidationFailure(
                f"COLD_ROUND_NORMALIZED_MISMATCH:{region_id}"
            )


def run_cache_test(root: Path, font_path: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    case = PRIMARY_CASES[0]
    image = render_text_rgb(case.source_text, font_path)
    crop = image_to_crop(image, region_id=case.region_id)
    png_bytes = ROICropEngine.preprocess_png(
        crop,
        scale=3,
        threshold=None,
    )
    path = root / "cache-case.png"
    write_verified_png(path, png_bytes)
    cache_directory = root / "cache"
    config = base_config(
        cache_directory,
        cache_enabled=True,
        privacy_sensitive=False,
    )

    with trace_tesseract_tsv_calls() as cold_trace:
        first = OCREngine(config).prepare_pipeline(path)
    first_normalized = LiveMarketReader().normalize_field(
        case.region_id,
        first.text,
    )
    if not strict_result_accepted(
        first,
        normalized_valid=first_normalized.valid,
        normalized_text=first_normalized.normalized_text,
        expected=case.expected,
        require_cold=True,
    ):
        raise ValidationFailure("CACHE_COLD_EXECUTION_INVALID")
    if cold_trace.count < 1:
        raise ValidationFailure(
            "CACHE_COLD_TESSERACT_NOT_EXECUTED"
        )

    with trace_tesseract_tsv_calls() as warm_trace:
        second = OCREngine(config).prepare_pipeline(path)
    second_normalized = LiveMarketReader().normalize_field(
        case.region_id,
        second.text,
    )
    if not second.cache_hit:
        raise ValidationFailure("WARM_CACHE_MISS")
    if warm_trace.count != 0:
        raise ValidationFailure(
            "WARM_CACHE_EXECUTED_TESSERACT"
        )
    if (
        second_normalized.normalized_text
        != first_normalized.normalized_text
    ):
        raise ValidationFailure(
            "WARM_CACHE_NORMALIZED_MISMATCH"
        )

    return {
        "cold_cache_hit": first.cache_hit,
        "cold_tsv_call_count": cold_trace.count,
        "warm_cache_hit": second.cache_hit,
        "warm_tsv_call_count": warm_trace.count,
        "cache_file_count": len(
            tuple(cache_directory.glob("*.json"))
        ),
    }


def run_private_cache_tests(
    root: Path,
    font_path: Path,
) -> dict[str, object]:
    results: dict[str, object] = {}
    for case in PRIMARY_CASES:
        if not case.privacy_sensitive:
            continue
        case_root = root / case.region_id
        case_root.mkdir(parents=True, exist_ok=True)
        image = render_text_rgb(case.source_text, font_path)
        crop = image_to_crop(image, region_id=case.region_id)
        png = ROICropEngine.preprocess_png(
            crop,
            scale=3,
            threshold=None,
        )
        path = case_root / "private.png"
        write_verified_png(path, png)
        cache_directory = case_root / "private-cache"
        with trace_tesseract_tsv_calls() as trace:
            result = OCREngine(
                base_config(
                    cache_directory,
                    cache_enabled=True,
                    privacy_sensitive=True,
                )
            ).prepare_pipeline(path)
        normalized = LiveMarketReader().normalize_field(
            case.region_id,
            result.text,
        )
        if not strict_result_accepted(
            result,
            normalized_valid=normalized.valid,
            normalized_text=normalized.normalized_text,
            expected=case.expected,
            require_cold=True,
        ):
            raise ValidationFailure(
                f"PRIVATE_CASE_INVALID:{case.region_id}"
            )
        if cache_directory.exists():
            raise ValidationFailure(
                f"PRIVATE_CACHE_CREATED:{case.region_id}"
            )
        results[case.region_id] = {
            "cache_directory_created": False,
            "tsv_call_count": trace.count,
            "reported_value": "REDACTED_SYNTHETIC_PRIVATE",
        }
    return results


def run_fallback_test(
    root: Path,
    font_path: Path,
) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    image = render_text_rgb("DEMO", font_path)
    crop = image_to_crop(image, region_id="ACCOUNT_TYPE")
    png = ROICropEngine.preprocess_png(
        crop,
        scale=3,
        threshold=None,
    )
    path = root / "fallback.png"
    write_verified_png(path, png)

    with trace_tesseract_tsv_calls() as trace:
        result = OCREngine(
            base_config(
                root / "fallback-cache",
                cache_enabled=False,
                privacy_sensitive=False,
                language="zzz_missing",
                fallback_language="eng",
            )
        ).prepare_pipeline(path)
    normalized = LiveMarketReader().normalize_field(
        "ACCOUNT_TYPE",
        result.text,
    )
    if not strict_result_accepted(
        result,
        normalized_valid=normalized.valid,
        normalized_text=normalized.normalized_text,
        expected="DEMO",
        require_cold=True,
    ):
        raise ValidationFailure(
            "ENGLISH_FALLBACK_RESULT_INVALID"
        )
    if (
        result.provider_language != "eng"
        or result.language_used != "eng"
    ):
        raise ValidationFailure(
            "ENGLISH_FALLBACK_LANGUAGE_BINDING_INVALID"
        )
    if trace.count < 1:
        raise ValidationFailure(
            "ENGLISH_FALLBACK_TESSERACT_NOT_EXECUTED"
        )
    return {
        "provider_language": result.provider_language,
        "execution_language": result.language_used,
        "language_valid": result.language_valid,
        "tsv_call_count": trace.count,
    }


def run_positive_extra_cases(
    root: Path,
    font_path: Path,
    numeric_font_path: Path,
) -> dict[str, object]:
    results: dict[str, object] = {}
    for index, case in enumerate(POSITIVE_EXTRA_CASES):
        item = run_case_variants(
            case,
            root=root / f"{index:02d}-{case.region_id}",
            font_path=font_path,
            numeric_font_path=numeric_font_path,
        )
        results[f"{index:02d}-{case.region_id}"] = {
            "normalized": item["normalized"],
            "best_confidence": item["best_confidence"],
            "valid_variant_count": item["valid_variant_count"],
            "tsv_call_count": item[
                "real_tesseract_tsv_call_count"
            ],
        }
    return results


def run_negative_controls(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    reader = LiveMarketReader()
    checks: list[bool] = []

    for field_id, raw_text in NEGATIVE_TEXT_CASES:
        checks.append(
            not reader.normalize_field(
                field_id,
                raw_text,
            ).valid
        )

    empty = root / "empty.png"
    empty.write_bytes(b"")
    checks.append(not OCRValidator().validate(empty).valid)

    try:
        TesseractOCRProvider(psm=-1)
    except ValueError:
        checks.append(True)
    else:
        checks.append(False)

    try:
        TesseractOCRProvider(psm=999)
    except ValueError:
        checks.append(True)
    else:
        checks.append(False)

    try:
        TesseractOCRProvider(timeout_seconds=0)
    except ValueError:
        checks.append(True)
    else:
        checks.append(False)

    for value in (-1, 101, float("nan")):
        try:
            OCREngine({"min_confidence": value})
        except ValueError:
            checks.append(True)
        else:
            checks.append(False)

    try:
        RGB24Crop(
            roi_id="BAD_HASH",
            x=0,
            y=0,
            width=1,
            height=1,
            sha256="0" * 64,
            pixel_bytes=b"\x00\x00\x00",
        )
    except ValueError:
        checks.append(True)
    else:
        checks.append(False)

    try:
        reconcile_primary_cases(PRIMARY_CASES[:-1])
    except ValidationFailure:
        checks.append(True)
    else:
        checks.append(False)

    try:
        reconcile_primary_cases(
            PRIMARY_CASES + (PRIMARY_CASES[0],)
        )
    except ValidationFailure:
        checks.append(True)
    else:
        checks.append(False)

    if not all(checks):
        failed = [
            index
            for index, passed in enumerate(checks)
            if not passed
        ]
        raise ValidationFailure(
            f"NEGATIVE_CONTROL_FAILED:{failed}"
        )
    return {
        "negative_control_count": len(checks),
        "negative_control_pass_count": sum(checks),
    }


def environment_metadata(
    font_path: Path,
    numeric_font_path: Path,
) -> dict[str, object]:
    tesseract_binary = shutil.which("tesseract")
    if tesseract_binary is None:
        raise ValidationFailure("TESSERACT_BINARY_NOT_FOUND")
    binary = str(Path(tesseract_binary).resolve())
    languages = command_output(
        [binary, "--list-langs"]
    ).splitlines()
    languages = [
        value.strip()
        for value in languages
        if value.strip()
        and not value.lower().startswith("list of")
    ]
    if "por" not in languages or "eng" not in languages:
        raise ValidationFailure(
            "REQUIRED_TESSERACT_LANGUAGES_MISSING"
        )
    return {
        "PYTHON_VERSION": sys.version.split()[0],
        "PILLOW_VERSION": PIL.__version__,
        "FREETYPE_VERSION": (
            features.version("freetype2") or "UNKNOWN"
        ),
        "NUMPY_VERSION": numpy.__version__,
        "FONT_BASENAME": font_path.name,
        "FONT_SHA256": sha256_file(font_path),
        "NUMERIC_FONT_BASENAME": numeric_font_path.name,
        "NUMERIC_FONT_SHA256": sha256_file(numeric_font_path),
        "TESSERACT_BINARY": binary,
        "TESSERACT_VERSION": command_output(
            [binary, "--version"]
        ).splitlines()[0],
        "TESSERACT_LANGUAGES": languages,
        "TESSDATA_POR_PACKAGE_VERSION": package_version(
            "tesseract-ocr-por"
        ),
        "TESSDATA_ENG_PACKAGE_VERSION": package_version(
            "tesseract-ocr-eng"
        ),
    }


def validate_synthetic_ocr() -> dict[str, object]:
    reconciliation = reconcile_primary_cases(PRIMARY_CASES)
    font_path = locate_font()
    numeric_font_path = locate_numeric_font()
    metadata = environment_metadata(font_path, numeric_font_path)
    temporary_path: Path | None = None

    with tempfile.TemporaryDirectory(
        prefix="predixai-b3-synthetic-ocr-"
    ) as temporary:
        temporary_path = Path(temporary)
        if temporary_path.stat().st_mode & 0o077:
            raise ValidationFailure(
                "TEMPORARY_DIRECTORY_PERMISSIONS_UNSAFE"
            )

        cold_a = run_cold_round(
            temporary_path / "cold-a",
            font_path,
            numeric_font_path,
        )
        cold_b = run_cold_round(
            temporary_path / "cold-b",
            font_path,
            numeric_font_path,
        )
        compare_cold_rounds(cold_a, cold_b)

        cache_result = run_cache_test(
            temporary_path / "cache-test",
            font_path,
        )
        private_cache = run_private_cache_tests(
            temporary_path / "private-cache-test",
            font_path,
        )
        fallback = run_fallback_test(
            temporary_path / "fallback-test",
            font_path,
        )
        extras = run_positive_extra_cases(
            temporary_path / "positive-extras",
            font_path,
            numeric_font_path,
        )
        negative_controls = run_negative_controls(
            temporary_path / "negative-controls"
        )

        result = {
            "PTP_ID": PTP_ID,
            "FINAL_STATUS": "PASS",
            **reconciliation,
            "SYNTHETIC_REGION_PASS_COUNT": cold_a[
                "pass_count"
            ],
            "COLD_RUN_A_TSV_CALL_COUNT": cold_a[
                "tsv_call_count"
            ],
            "COLD_RUN_B_TSV_CALL_COUNT": cold_b[
                "tsv_call_count"
            ],
            "COLD_RUN_NORMALIZED_RESULTS_MATCH": "YES",
            "REAL_TESSERACT_EXECUTED_IN_BOTH_COLD_RUNS": "YES",
            "WARM_CACHE_RUN": cache_result,
            "PRIVATE_CACHE_TESTS": private_cache,
            "FALLBACK_TEST": fallback,
            "POSITIVE_EXTRA_CASES": extras,
            "NEGATIVE_CONTROLS": negative_controls,
            "SKIPPED_REAL_OCR_TEST_COUNT": 0,
            "BROKER_CAPTURE_EXECUTED": "NO",
            "OCR_LIVE_EXECUTED": "NO",
            "MANUAL_CALIBRATION_EXECUTED": "NO",
            "BROKER_CLICK_EXECUTED": "NO",
            "ORDER_EXECUTED": "NO",
            "TEMPORARY_FILES_REMOVED": "PENDING_CONTEXT_EXIT",
            "ENVIRONMENT": metadata,
            "COLD_RUN_A": cold_a,
            "COLD_RUN_B": cold_b,
        }

    removed = (
        temporary_path is not None
        and not temporary_path.exists()
    )
    if not removed:
        raise ValidationFailure(
            "TEMPORARY_DIRECTORY_NOT_REMOVED"
        )
    result["TEMPORARY_FILES_REMOVED"] = "YES"
    return result


def run_smoke_real_ocr() -> dict[str, object]:
    font_path = locate_font()
    with tempfile.TemporaryDirectory(
        prefix="predixai-b3-smoke-"
    ) as temporary:
        root = Path(temporary)
        case = SyntheticCase("PAYOUT", "85%", "85%")
        image = render_text_rgb(case.source_text, font_path)
        crop = image_to_crop(image, region_id=case.region_id)
        path = root / "smoke.png"
        write_verified_png(
            path,
            ROICropEngine.preprocess_png(
                crop,
                scale=3,
                threshold=None,
            ),
        )
        with trace_tesseract_tsv_calls() as trace:
            result = OCREngine(
                base_config(
                    root / "cache",
                    cache_enabled=False,
                    privacy_sensitive=False,
                )
            ).prepare_pipeline(path)
        normalized = LiveMarketReader().normalize_field(
            case.region_id,
            result.text,
        )
        passed = strict_result_accepted(
            result,
            normalized_valid=normalized.valid,
            normalized_text=normalized.normalized_text,
            expected=case.expected,
            require_cold=True,
        )
        if not passed or trace.count < 1:
            raise ValidationFailure(
                "REAL_OCR_SMOKE_TEST_FAILED"
            )
        return {
            "status": "PASS",
            "tsv_call_count": trace.count,
            "confidence": result.confidence,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--smoke-only",
        action="store_true",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = (
            run_smoke_real_ocr()
            if args.smoke_only
            else validate_synthetic_ocr()
        )
    except Exception as exc:
        payload = {
            "PTP_ID": PTP_ID,
            "FINAL_STATUS": "FAIL",
            "FAIL_REASON": (
                f"{type(exc).__name__}:{exc}"
            ),
            "BROKER_CAPTURE_EXECUTED": "NO",
            "OCR_LIVE_EXECUTED": "NO",
            "MANUAL_CALIBRATION_EXECUTED": "NO",
            "BROKER_CLICK_EXECUTED": "NO",
            "ORDER_EXECUTED": "NO",
        }
        output = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        if args.output_json:
            args.output_json.write_text(
                output + "\n",
                encoding="utf-8",
            )
        if not args.quiet:
            print(output)
        return 1

    output = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if args.output_json:
        args.output_json.write_text(
            output + "\n",
            encoding="utf-8",
        )
    if not args.quiet:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
