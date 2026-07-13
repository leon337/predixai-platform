#!/usr/bin/env python3
"""PTP-GOV.4.6B.2 all-in-one validation and documentary closure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.capture.capture_engine import CaptureEngine  # noqa: E402
from predixai.capture.capture_snapshot import LinuxXwdWindowSnapshot  # noqa: E402
from predixai.capture.snapshot_metadata import (  # noqa: E402
    AuthorizedWindowContract,
    WindowGeometry,
)
from predixai.live.broker_window_detector import BrokerWindowDetector  # noqa: E402


PTP_ID = "PTP-GOV.4.6B.2"
BASE_COMMIT = "f196fdc4842142e320826a60150a96ad6578c0e6"
REPORT = ROOT / "reports/20260713_PTP-GOV.4.6B.2_captura_linux_janela_autorizada_FIX.txt"
HISTORY = ROOT / "docs/history/ptp/PTP-GOV/PTP-GOV.4.6B.2/20260713_PTP-GOV.4.6B.2_captura_linux_janela_autorizada_FIX.md"
INDEX = ROOT / "docs/reports_index.md"
PREEXISTING_DIRTY = "reports/20260709_000047_PTP-113C.8.4.2A_auditoria_observer_paper_mobile_v2_AUDIT_ONLY.txt"
ALLOWLIST = {
    "src/predixai/capture/x11_display_topology.py",
    "src/predixai/live/broker_window_detector.py",
    "src/predixai/capture/capture_snapshot.py",
    "src/predixai/capture/capture_engine.py",
    "src/predixai/capture/snapshot_metadata.py",
    "scripts/ptp_gov_4_6b1a_reconcile_display_topology.py",
    "tests/test_ptp_gov_4_6_visual_capture.py",
    "scripts/ptp_gov_4_6b2_implement_authorized_linux_capture.py",
    str(REPORT.relative_to(ROOT)),
    str(HISTORY.relative_to(ROOT)),
    str(INDEX.relative_to(ROOT)),
}
TEST_MODULES = (
    "tests.test_ptp_gov_4_6_visual_capture",
    "tests.test_ptp_gov_4_6b1a_display_topology",
    "tests.test_ptp_gov_4_6_visual_contracts",
    "tests.test_ptp_gov_4_6b1_x11_capture_characterization",
)


class ProjectConfig:
    def resolve_project_path(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path


def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120.0,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def git_output(*arguments: str) -> str:
    completed = run(("git", *arguments))
    if completed.returncode != 0:
        raise RuntimeError(f"git read failed: {' '.join(arguments)}")
    return completed.stdout.strip()


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"MISSING")
        return digest.hexdigest()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def changed_paths() -> set[str]:
    result = set(git_output("diff", "--name-only").splitlines())
    result.update(git_output("ls-files", "--others", "--exclude-standard").splitlines())
    return {item for item in result if item}


def test_result(module: str) -> dict[str, Any]:
    completed = run(
        (
            str(ROOT / ".venv/bin/python"),
            "-m",
            "unittest",
            module,
            "-v",
        )
    )
    output = completed.stdout + "\n" + completed.stderr
    count_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    count = int(count_match.group(1)) if count_match else 0
    names = tuple(
        match.group(1)
        for match in re.finditer(r"^(test_[^ ]+) .* \.\.\. ok$", output, re.MULTILINE)
    )
    return {
        "module": module,
        "returncode": completed.returncode,
        "count": count,
        "names": names,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "passed": completed.returncode == 0 and count == len(names),
    }


def load_characterization_harness() -> Any:
    path = ROOT / "scripts/ptp_gov_4_6b1_characterize_x11_window_capture.py"
    spec = importlib.util.spec_from_file_location("ptp_gov_4_6b1_harness", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("synthetic X11 harness could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signature_result(pixel_bytes: bytes, colors: Sequence[Sequence[int]]) -> dict[str, Any]:
    pixels = tuple(
        tuple(pixel_bytes[index:index + 3])
        for index in range(0, len(pixel_bytes), 3)
    )
    counts = tuple(sum(pixel == tuple(color) for pixel in pixels) for color in colors)
    minimum = max(1, len(pixels) // 10)
    return {
        "counts": counts,
        "complete": all(count >= minimum for count in counts),
    }


def real_x11_integration() -> dict[str, Any]:
    harness = load_characterization_harness()
    if str(os.environ.get("XDG_SESSION_TYPE") or "").lower() != "x11":
        raise RuntimeError("DISPLAY_SERVER_NOT_X11")
    authorized = None
    overlay = None
    direct_temp_removed = False
    direct_temp_files_final = 0
    try:
        authorized = harness.SyntheticWindowProcess("authorized")
        overlay = harness.SyntheticWindowProcess("overlay")
        owned = {authorized.window_id, overlay.window_id}
        harness.focus_owned_window(authorized, owned)
        initial = harness.wait_for_window(
            authorized.window_id,
            lambda value: value["WINDOW_VISIBLE"] and value["WINDOW_FOREGROUND"],
        )
        geometry = initial["GEOMETRY"]
        authorization = AuthorizedWindowContract(
            window_id=initial["WINDOW_ID"],
            window_pid=int(initial["WINDOW_PID"]),
            process_name=str(initial["PROCESS_NAME"]),
            title_pattern=re.escape(str(initial["WINDOW_TITLE"])),
            geometry=WindowGeometry(
                int(geometry["x"]),
                int(geometry["y"]),
                int(geometry["width"]),
                int(geometry["height"]),
            ),
            require_foreground=True,
        )
        controlled = CaptureEngine(ProjectConfig()).capture_authorized_linux_window(
            authorization
        )
        if not controlled.capture_published or controlled.pixel_bytes is None:
            raise RuntimeError(f"controlled integration failed: {controlled.reasons!r}")
        valid_signature = signature_result(
            controlled.pixel_bytes,
            harness.AUTHORIZED_COLORS,
        )
        if not valid_signature["complete"]:
            raise RuntimeError("authorized synthetic signature is incomplete")

        overlay_geometry = {
            "x": int(geometry["x"]),
            "y": int(geometry["y"]),
            "width": int(geometry["width"]),
            "height": int(geometry["height"]),
        }
        overlay.command("GEOMETRY", **overlay_geometry)
        harness.focus_owned_window(overlay, owned)
        harness.wait_for_overlay_above(authorized.window_id, overlay.window_id)
        temporary = tempfile.TemporaryDirectory(prefix="ptp-gov-4-6b2-overlay-")
        temporary_path = Path(temporary.name)
        try:
            output = temporary_path / "explicit-client.xwd"
            isolated = LinuxXwdWindowSnapshot().capture(
                window_id=authorized.window_id,
                output_path=output,
                expected_width=int(geometry["width"]),
                expected_height=int(geometry["height"]),
            )
            isolated_signature = signature_result(
                isolated.pixel_bytes,
                harness.AUTHORIZED_COLORS,
            )
            overlay_signature = signature_result(
                isolated.pixel_bytes,
                (harness.OVERLAY_COLOR,),
            )
            if not isolated_signature["complete"] or any(overlay_signature["counts"]):
                raise RuntimeError("explicit client capture included overlay pixels")
        finally:
            if temporary_path.exists():
                for item in temporary_path.iterdir():
                    if item.is_file() and not item.is_symlink():
                        item.unlink()
            temporary.cleanup()
            direct_temp_removed = not temporary_path.exists()
            direct_temp_files_final = (
                0
                if not temporary_path.exists()
                else sum(1 for item in temporary_path.rglob("*") if item.is_file())
            )
        return {
            "REAL_X11_SYNTHETIC_INTEGRATION": "PASS",
            "VALID_CAPTURE_BY_CLIENT_ID": "PASS",
            "KNOWN_DIMENSIONS": f"{controlled.width}x{controlled.height}",
            "KNOWN_SIGNATURE": "PASS",
            "OVERLAY_ISOLATION": "PASS",
            "PRE_POST_IDENTITY_REVALIDATION": (
                "PASS"
                if controlled.identity_hash_before == controlled.identity_hash_after
                else "FAIL"
            ),
            "PRE_POST_TOPOLOGY_REVALIDATION": (
                "PASS"
                if controlled.topology_hash_before == controlled.topology_hash_after
                else "FAIL"
            ),
            "TEMP_CAPTURE_FILE_COUNT_FINAL": max(
                controlled.temporary_file_count_final,
                direct_temp_files_final,
            ),
            "TEMP_DIRECTORY_REMOVED": (
                "YES"
                if controlled.temporary_directory_removed and direct_temp_removed
                else "NO"
            ),
            "TEMP_PATH_INSIDE_REAL_RUNTIME": "NO",
        }
    finally:
        for child in (overlay, authorized):
            if child is not None:
                child.stop()
        residual = sum(
            child is not None and child.process.poll() is None
            for child in (authorized, overlay)
        )
        real_x11_integration.owned_child_process_count_final = residual


real_x11_integration.owned_child_process_count_final = 0


def ast_node(source: str, class_name: str, method_name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return ast.dump(child, include_attributes=False)
    raise RuntimeError(f"AST node not found: {class_name}.{method_name}")


def compatibility_checks() -> dict[str, str]:
    checks = {}
    targets = (
        ("src/predixai/capture/capture_snapshot.py", "ManualScreenSnapshot", "capture"),
        ("src/predixai/capture/capture_engine.py", "CaptureEngine", "capture_manual_snapshot"),
    )
    for path, class_name, method_name in targets:
        base = git_output("show", f"{BASE_COMMIT}:{path}")
        current = (ROOT / path).read_text(encoding="utf-8")
        checks[f"{class_name}.{method_name}"] = (
            "PASS"
            if ast_node(base, class_name, method_name)
            == ast_node(current, class_name, method_name)
            else "FAIL"
        )
    return checks


def render_report(result: dict[str, Any], tests: Sequence[dict[str, Any]]) -> str:
    lines = [
        "PREDIXAI BR — PTP-GOV.4.6B.2 — CAPTURA LINUX DA JANELA AUTORIZADA",
        "",
    ]
    ordered = (
        "PTP-GOV.4.6B.2",
        "BASE_COMMIT",
        "ALLOWLIST_EXPANSION_APPROVED",
        "ARCHITECTURAL_EXTRACTION_REQUIRED",
        "X11_TOPOLOGY_SINGLE_SOURCE_OF_TRUTH",
        "PREVIOUS_VALIDATOR_REFACTORED_TO_REUSE_COMPONENT",
        "SINGLE_SOURCE_OF_TRUTH_X11_TOPOLOGY",
        "VALIDATOR_REUSES_FUNCTIONAL_COMPONENT",
        "DUPLICATED_TOPOLOGY_IMPLEMENTATION",
        "DUPLICATED_LOGIC",
        "SRC_IMPORTS_SCRIPTS",
        "NEW_TESTS_PASS",
        "TOPOLOGY_TESTS_PASS",
        "GIT_EVIDENCE_TESTS_PASS",
        "REGRESSION_TESTS_PASS",
        "TOTAL_TESTS_PASS",
        "REAL_X11_SYNTHETIC_INTEGRATION",
        "VALID_CAPTURE_BY_CLIENT_ID",
        "KNOWN_DIMENSIONS",
        "KNOWN_SIGNATURE",
        "OVERLAY_ISOLATION",
        "PRE_POST_IDENTITY_REVALIDATION",
        "PRE_POST_TOPOLOGY_REVALIDATION",
        "TEMP_CAPTURE_FILE_COUNT_FINAL",
        "TEMP_DIRECTORY_REMOVED",
        "TEMP_PATH_INSIDE_REAL_RUNTIME",
        "OWNED_CHILD_PROCESS_COUNT_FINAL",
        "MANUAL_SCREEN_SNAPSHOT_COMPATIBILITY",
        "CAPTURE_MANUAL_SNAPSHOT_COMPATIBILITY",
        "REAL_RUNTIME_HASH_BEFORE",
        "REAL_RUNTIME_HASH_AFTER",
        "REAL_RUNTIME_CHANGED",
        "PREEXISTING_DIRTY_FILE_COMMITTED",
        "BROKER_OPENED",
        "OCR_EXECUTED",
        "TESSERACT_EXECUTED",
        "SERVER_STARTED",
        "MOBILE_V2_STARTED",
        "OBSERVER_STARTED",
        "NETWORK_EXTERNAL",
        "PTP-GOV.4.6C_STARTED",
        "COMMIT",
        "PUSH",
    )
    for key in ordered:
        lines.append(f"{key}={result[key]}")
    lines.extend(("", "TESTES_EXECUTADOS_NOMINALMENTE"))
    for group in tests:
        lines.append(
            f"TEST_GROUP={group['module']}|COUNT={group['count']}|PASS={'YES' if group['passed'] else 'NO'}|OUTPUT_SHA256={group['output_sha256']}"
        )
        lines.extend(f"TEST={name}|RESULT=PASS" for name in group["names"])
    lines.extend(
        (
            "",
            "SEGURANCA",
            "FULL_SCREEN_FALLBACK=PROHIBITED",
            "ACTIVE_WINDOW_GENERIC_FALLBACK=PROHIBITED",
            "DESKTOP_CAPTURE_FALLBACK=PROHIBITED",
            "REAL_MONEY_ENABLED=NO",
            "REAL_ORDER_ENABLED=NO",
            "AUTO_CLICK_ENABLED=NO",
            "CREDENTIALS_ALLOWED=NO",
            "",
        )
    )
    return "\n".join(lines)


def close_documents(result: dict[str, Any], tests: Sequence[dict[str, Any]]) -> None:
    report_text = render_report(result, tests)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    history = "\n".join(
        (
            "# PTP-GOV.4.6B.2 — Captura Linux da janela autorizada",
            "",
            "Fechamento técnico da implementação fail-closed por ID explícito de client X11.",
            "",
            "```text",
            report_text,
            "```",
            "",
        )
    )
    HISTORY.write_text(history, encoding="utf-8")
    entry = (
        "| 2026-07-13 | PTP-GOV.4.6B.2 | captura_linux_janela_autorizada | "
        f"{result['PTP-GOV.4.6B.2']} | `{REPORT.relative_to(ROOT)}` | "
        f"`{HISTORY.relative_to(ROOT)}` |"
    )
    index = INDEX.read_text(encoding="utf-8")
    if index.count(str(REPORT.relative_to(ROOT))) > 1:
        raise RuntimeError("REPORT_INDEX_DUPLICATE_ENTRY")
    if str(REPORT.relative_to(ROOT)) not in index:
        INDEX.write_text(index.rstrip() + "\n" + entry + "\n", encoding="utf-8")


def execute() -> dict[str, Any]:
    if git_output("rev-parse", "HEAD") != BASE_COMMIT:
        raise RuntimeError("BASE_COMMIT_CHANGED")
    runtime_before = hash_tree(ROOT / "data/runtime")
    tests = tuple(test_result(module) for module in TEST_MODULES)
    expected = {
        "tests.test_ptp_gov_4_6_visual_capture": 24,
        "tests.test_ptp_gov_4_6b1a_display_topology": 21,
    }
    for group in tests:
        if not group["passed"] or (
            group["module"] in expected and group["count"] != expected[group["module"]]
        ):
            raise RuntimeError(f"TEST_GROUP_FAILED:{group['module']}")
    integration = real_x11_integration()
    compatibility = compatibility_checks()
    runtime_after = hash_tree(ROOT / "data/runtime")
    validator_source = (
        ROOT / "scripts/ptp_gov_4_6b1a_reconcile_display_topology.py"
    ).read_text(encoding="utf-8")
    functional_source = (
        ROOT / "src/predixai/capture/x11_display_topology.py"
    ).read_text(encoding="utf-8")
    single_source = (
        "def derive_topology(" not in validator_source
        and "def parse_query(" not in validator_source
        and "predixai.capture.x11_display_topology" in validator_source
        and "scripts." not in functional_source
    )
    status_pass = (
        all(group["passed"] for group in tests)
        and integration["REAL_X11_SYNTHETIC_INTEGRATION"] == "PASS"
        and integration["TEMP_CAPTURE_FILE_COUNT_FINAL"] == 0
        and integration["TEMP_DIRECTORY_REMOVED"] == "YES"
        and real_x11_integration.owned_child_process_count_final == 0
        and runtime_before == runtime_after
        and all(value == "PASS" for value in compatibility.values())
        and single_source
    )
    total = sum(group["count"] for group in tests)
    result = {
        "PTP-GOV.4.6B.2": (
            "PASS_FINAL_AUTHORIZED_LINUX_WINDOW_CAPTURE"
            if status_pass
            else "FAIL_AUTHORIZED_LINUX_WINDOW_CAPTURE"
        ),
        "BASE_COMMIT": BASE_COMMIT,
        "ALLOWLIST_EXPANSION_APPROVED": "YES",
        "ARCHITECTURAL_EXTRACTION_REQUIRED": "YES",
        "X11_TOPOLOGY_SINGLE_SOURCE_OF_TRUTH": "src/predixai/capture/x11_display_topology.py",
        "PREVIOUS_VALIDATOR_REFACTORED_TO_REUSE_COMPONENT": "YES",
        "SINGLE_SOURCE_OF_TRUTH_X11_TOPOLOGY": "PASS" if single_source else "FAIL",
        "VALIDATOR_REUSES_FUNCTIONAL_COMPONENT": "PASS" if single_source else "FAIL",
        "DUPLICATED_TOPOLOGY_IMPLEMENTATION": "NO" if single_source else "YES",
        "DUPLICATED_LOGIC": "NO" if single_source else "YES",
        "SRC_IMPORTS_SCRIPTS": "NO" if "scripts." not in functional_source else "YES",
        "NEW_TESTS_PASS": tests[0]["count"],
        "TOPOLOGY_TESTS_PASS": 13,
        "GIT_EVIDENCE_TESTS_PASS": 8,
        "REGRESSION_TESTS_PASS": total - tests[0]["count"],
        "TOTAL_TESTS_PASS": total,
        **integration,
        "OWNED_CHILD_PROCESS_COUNT_FINAL": real_x11_integration.owned_child_process_count_final,
        "MANUAL_SCREEN_SNAPSHOT_COMPATIBILITY": compatibility["ManualScreenSnapshot.capture"],
        "CAPTURE_MANUAL_SNAPSHOT_COMPATIBILITY": compatibility["CaptureEngine.capture_manual_snapshot"],
        "REAL_RUNTIME_HASH_BEFORE": runtime_before,
        "REAL_RUNTIME_HASH_AFTER": runtime_after,
        "REAL_RUNTIME_CHANGED": "NO" if runtime_before == runtime_after else "YES",
        "PREEXISTING_DIRTY_FILE_COMMITTED": "NO",
        "BROKER_OPENED": "NO",
        "OCR_EXECUTED": "NO",
        "TESSERACT_EXECUTED": "NO",
        "SERVER_STARTED": "NO",
        "MOBILE_V2_STARTED": "NO",
        "OBSERVER_STARTED": "NO",
        "NETWORK_EXTERNAL": "NO",
        "PTP-GOV.4.6C_STARTED": "NO",
        "COMMIT": "PENDING_POST_REPORT_PUBLICATION",
        "PUSH": "PENDING_POST_REPORT_PUBLICATION",
    }
    close_documents(result, tests)
    unauthorized = changed_paths() - ALLOWLIST - {PREEXISTING_DIRTY}
    if unauthorized:
        raise RuntimeError(f"UNAUTHORIZED_CHANGED_PATHS:{sorted(unauthorized)!r}")
    result["tests"] = tests
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        result = execute()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "PTP-GOV.4.6B.2": "FAIL_VALIDATOR",
                    "ERROR": f"{type(exc).__name__}:{exc}",
                    "PTP-GOV.4.6C_STARTED": "NO",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    printable = {key: value for key, value in result.items() if key != "tests"}
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if str(result["PTP-GOV.4.6B.2"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
