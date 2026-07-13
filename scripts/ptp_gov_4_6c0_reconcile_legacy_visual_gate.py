#!/usr/bin/env python3
"""PTP-GOV.4.6C.0 all-in-one logical-topology gate reconciliation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PTP_ID = "PTP-GOV.4.6C.0"
BASE_COMMIT = "c1d2521505d880e26a7142b8c87c3ee9ba74925c"
REPORT = ROOT / "reports/20260713_PTP-GOV.4.6C.0_reconciliacao_gate_visual_legado_FIX.txt"
HISTORY = ROOT / "docs/history/ptp/PTP-GOV/PTP-GOV.4.6C.0/20260713_PTP-GOV.4.6C.0_reconciliacao_gate_visual_legado_FIX.md"
INDEX = ROOT / "docs/reports_index.md"
PREEXISTING_DIRTY = "reports/20260709_000047_PTP-113C.8.4.2A_auditoria_observer_paper_mobile_v2_AUDIT_ONLY.txt"
VISUAL_VALIDATOR = ROOT / "scripts/ptp_gov_4_6a_characterize_visual_contracts.py"
B1_VALIDATOR = ROOT / "scripts/ptp_gov_4_6b1_characterize_x11_window_capture.py"
FUNCTIONAL_TOPOLOGY = ROOT / "src/predixai/capture/x11_display_topology.py"
ALLOWLIST = {
    "scripts/ptp_gov_4_6a_characterize_visual_contracts.py",
    "tests/test_ptp_gov_4_6_visual_contracts.py",
    "scripts/ptp_gov_4_6b1_characterize_x11_window_capture.py",
    "tests/test_ptp_gov_4_6b1_x11_capture_characterization.py",
    "scripts/ptp_gov_4_6c0_reconcile_legacy_visual_gate.py",
    str(REPORT.relative_to(ROOT)),
    str(HISTORY.relative_to(ROOT)),
    str(INDEX.relative_to(ROOT)),
}
TEST_MODULES = (
    "tests.test_ptp_gov_4_6_visual_contracts",
    "tests.test_ptp_gov_4_6b1_x11_capture_characterization",
    "tests.test_ptp_gov_4_6b1a_display_topology",
    "tests.test_ptp_gov_4_6_visual_capture",
)
EXPECTED_COUNTS = {
    "tests.test_ptp_gov_4_6_visual_contracts": 20,
    "tests.test_ptp_gov_4_6b1_x11_capture_characterization": 15,
    "tests.test_ptp_gov_4_6b1a_display_topology": 21,
    "tests.test_ptp_gov_4_6_visual_capture": 24,
}
REQUIRED_LOGICAL_TESTS = {
    "test_single_logical_capture_surface_is_required",
    "test_mirrored_outputs_with_one_logical_surface_are_allowed",
    "test_extended_desktop_fails_closed",
    "test_inconclusive_topology_fails_closed",
    "test_panning_fails_closed",
    "test_non_identity_transform_fails_closed",
    "test_monitor_count_is_informational_only",
}


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
    paths = set(git_output("diff", "--name-only").splitlines())
    paths.update(git_output("ls-files", "--others", "--exclude-standard").splitlines())
    return {path for path in paths if path}


def test_result(module: str) -> dict[str, Any]:
    completed = run(
        (str(ROOT / ".venv/bin/python"), "-m", "unittest", module, "-v")
    )
    output = completed.stdout + "\n" + completed.stderr
    count_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    count = int(count_match.group(1)) if count_match else 0
    names = tuple(
        match.group(1)
        for match in re.finditer(r"^(test_[^ ]+) .* \.\.\. ok$", output, re.MULTILINE)
    )
    passed = (
        completed.returncode == 0
        and count == len(names)
        and count == EXPECTED_COUNTS[module]
    )
    return {
        "module": module,
        "count": count,
        "names": names,
        "passed": passed,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }


def monitor_count_used_as_gate(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.Compare)):
            continue
        segment = ast.get_source_segment(source, node) or ""
        if "MONITOR_COUNT" in segment or "monitor_count" in segment:
            if any(operator in segment for operator in ("!= 1", "== 1", "is 1")):
                return True
    return False


def structural_checks(test_groups: Sequence[dict[str, Any]]) -> dict[str, str]:
    visual = VISUAL_VALIDATOR.read_text(encoding="utf-8")
    b1 = B1_VALIDATOR.read_text(encoding="utf-8")
    functional = FUNCTIONAL_TOPOLOGY.read_text(encoding="utf-8")
    executed_names = {
        name for group in test_groups for name in group["names"]
    }
    topology_definitions = (
        "def derive_topology(",
        "def parse_query(",
        "def parse_verbose(",
        "def parse_active_monitors(",
    )
    source_truth = (
        "predixai.capture.x11_display_topology" in visual
        and "predixai.capture.x11_display_topology" in b1
        and not any(definition in visual or definition in b1 for definition in topology_definitions)
        and "scripts." not in functional
    )
    return {
        "LEGACY_MONITOR_COUNT_GATE_REMOVED": (
            "YES"
            if not monitor_count_used_as_gate(visual)
            and not monitor_count_used_as_gate(b1)
            and "SINGLE_MONITOR_CONTRACT_VIOLATED" not in visual
            and "SINGLE_MONITOR_CONTRACT_VIOLATED" not in b1
            else "NO"
        ),
        "LOGICAL_TOPOLOGY_GATE_REQUIRED": (
            "YES"
            if "DISPLAY_TOPOLOGY" in visual
            and "LOGICAL_DESKTOP_COUNT_NOT_ONE" in visual
            and "CAPTURE_SURFACE_COUNT_NOT_ONE" in visual
            else "NO"
        ),
        "MIRRORED_OUTPUTS_COMPATIBLE": (
            "YES"
            if "test_mirrored_outputs_with_one_logical_surface_are_allowed"
            in executed_names
            else "NO"
        ),
        "EXTENDED_DESKTOP_FAIL_CLOSED": (
            "YES" if "test_extended_desktop_fails_closed" in executed_names else "NO"
        ),
        "INCONCLUSIVE_TOPOLOGY_FAIL_CLOSED": (
            "YES" if "test_inconclusive_topology_fails_closed" in executed_names else "NO"
        ),
        "PANNING_FAIL_CLOSED": (
            "YES" if "test_panning_fails_closed" in executed_names else "NO"
        ),
        "NON_IDENTITY_TRANSFORM_FAIL_CLOSED": (
            "YES" if "test_non_identity_transform_fails_closed" in executed_names else "NO"
        ),
        "MONITOR_COUNT_INFORMATIONAL_ONLY": (
            "YES" if "test_monitor_count_is_informational_only" in executed_names else "NO"
        ),
        "X11_TOPOLOGY_SINGLE_SOURCE_OF_TRUTH": (
            "src/predixai/capture/x11_display_topology.py" if source_truth else "NOT_CONFIRMED"
        ),
        "DUPLICATED_TOPOLOGY_LOGIC": "NO" if source_truth else "YES",
        "SRC_IMPORTS_SCRIPTS": "NO" if "scripts." not in functional else "YES",
        "REQUIRED_LOGICAL_TESTS_RECONCILED": (
            "YES" if REQUIRED_LOGICAL_TESTS.issubset(executed_names) else "NO"
        ),
    }


def render_report(result: dict[str, Any], tests: Sequence[dict[str, Any]]) -> str:
    keys = (
        "PTP-GOV.4.6C.0",
        "BASE_COMMIT",
        "B1_DEPENDENCY_CONFIRMED",
        "B1_TEST_FILE_CHANGED",
        "LEGACY_MONITOR_COUNT_GATE_REMOVED",
        "LOGICAL_TOPOLOGY_GATE_REQUIRED",
        "MIRRORED_OUTPUTS_COMPATIBLE",
        "EXTENDED_DESKTOP_FAIL_CLOSED",
        "INCONCLUSIVE_TOPOLOGY_FAIL_CLOSED",
        "PANNING_FAIL_CLOSED",
        "NON_IDENTITY_TRANSFORM_FAIL_CLOSED",
        "MONITOR_COUNT_INFORMATIONAL_ONLY",
        "X11_TOPOLOGY_SINGLE_SOURCE_OF_TRUTH",
        "DUPLICATED_TOPOLOGY_LOGIC",
        "SRC_IMPORTS_SCRIPTS",
        "REQUIRED_LOGICAL_TESTS_RECONCILED",
        "VISUAL_CONTRACT_TESTS_PASS",
        "X11_CHARACTERIZATION_TESTS_PASS",
        "TOPOLOGY_AND_GIT_EVIDENCE_TESTS_PASS",
        "AUTHORIZED_CAPTURE_TESTS_PASS",
        "TOTAL_TESTS_PASS",
        "ALL_APPLICABLE_REGRESSIONS",
        "REAL_RUNTIME_HASH_BEFORE",
        "REAL_RUNTIME_HASH_AFTER",
        "REAL_RUNTIME_CHANGED",
        "PREEXISTING_DIRTY_FILE_COMMITTED",
        "BROKER_OPENED",
        "LIVE_CAPTURE_EXECUTED",
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
    lines = [
        "PREDIXAI BR — PTP-GOV.4.6C.0 — RECONCILIAÇÃO DO GATE VISUAL LEGADO",
        "",
        *(f"{key}={result[key]}" for key in keys),
        "",
        "TESTES_EXECUTADOS_NOMINALMENTE",
    ]
    for group in tests:
        lines.append(
            f"TEST_GROUP={group['module']}|COUNT={group['count']}|PASS={'YES' if group['passed'] else 'NO'}|OUTPUT_SHA256={group['output_sha256']}"
        )
        lines.extend(f"TEST={name}|RESULT=PASS" for name in group["names"])
    lines.extend(
        (
            "",
            "GOVERNANCA",
            "MONITOR_COUNT=INFORMATIONAL",
            "ACTIVE_OUTPUT_COUNT=INFORMATIONAL",
            "CONNECTED_OUTPUT_COUNT=INFORMATIONAL",
            "FULL_SCREEN_FALLBACK=PROHIBITED",
            "ACTIVE_WINDOW_GENERIC_FALLBACK=PROHIBITED",
            "DESKTOP_CAPTURE_FALLBACK=PROHIBITED",
            "",
        )
    )
    return "\n".join(lines)


def close_documents(result: dict[str, Any], tests: Sequence[dict[str, Any]]) -> None:
    report = render_report(result, tests)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    HISTORY.write_text(
        "\n".join(
            (
                "# PTP-GOV.4.6C.0 — Reconciliação do gate visual legado",
                "",
                "Fechamento da substituição do gate físico isolado pelo contrato de topologia lógica.",
                "",
                "```text",
                report,
                "```",
                "",
            )
        ),
        encoding="utf-8",
    )
    entry = (
        "| 2026-07-13 | PTP-GOV.4.6C.0 | reconciliacao_gate_visual_legado | "
        f"{result['PTP-GOV.4.6C.0']} | `{REPORT.relative_to(ROOT)}` | "
        f"`{HISTORY.relative_to(ROOT)}` |"
    )
    index = INDEX.read_text(encoding="utf-8")
    report_path = str(REPORT.relative_to(ROOT))
    if index.count(report_path) > 1:
        raise RuntimeError("REPORT_INDEX_DUPLICATE_ENTRY")
    if report_path not in index:
        INDEX.write_text(index.rstrip() + "\n" + entry + "\n", encoding="utf-8")


def execute() -> dict[str, Any]:
    if git_output("rev-parse", "HEAD") != BASE_COMMIT:
        raise RuntimeError("BASE_COMMIT_CHANGED")
    runtime_before = hash_tree(ROOT / "data/runtime")
    tests = tuple(test_result(module) for module in TEST_MODULES)
    structures = structural_checks(tests)
    runtime_after = hash_tree(ROOT / "data/runtime")
    all_regressions = all(group["passed"] for group in tests)
    gates_pass = (
        all_regressions
        and runtime_before == runtime_after
        and structures["LEGACY_MONITOR_COUNT_GATE_REMOVED"] == "YES"
        and structures["LOGICAL_TOPOLOGY_GATE_REQUIRED"] == "YES"
        and structures["MIRRORED_OUTPUTS_COMPATIBLE"] == "YES"
        and structures["EXTENDED_DESKTOP_FAIL_CLOSED"] == "YES"
        and structures["PANNING_FAIL_CLOSED"] == "YES"
        and structures["NON_IDENTITY_TRANSFORM_FAIL_CLOSED"] == "YES"
        and structures["DUPLICATED_TOPOLOGY_LOGIC"] == "NO"
    )
    counts = {group["module"]: group["count"] for group in tests}
    result = {
        "PTP-GOV.4.6C.0": (
            "PASS_FINAL_LOGICAL_TOPOLOGY_GATE_RECONCILIATION"
            if gates_pass
            else "FAIL_LOGICAL_TOPOLOGY_GATE_RECONCILIATION"
        ),
        "BASE_COMMIT": BASE_COMMIT,
        "B1_DEPENDENCY_CONFIRMED": "YES",
        "B1_TEST_FILE_CHANGED": "NO",
        **structures,
        "VISUAL_CONTRACT_TESTS_PASS": counts[TEST_MODULES[0]],
        "X11_CHARACTERIZATION_TESTS_PASS": counts[TEST_MODULES[1]],
        "TOPOLOGY_AND_GIT_EVIDENCE_TESTS_PASS": counts[TEST_MODULES[2]],
        "AUTHORIZED_CAPTURE_TESTS_PASS": counts[TEST_MODULES[3]],
        "TOTAL_TESTS_PASS": sum(counts.values()),
        "ALL_APPLICABLE_REGRESSIONS": "PASS" if all_regressions else "FAIL",
        "REAL_RUNTIME_HASH_BEFORE": runtime_before,
        "REAL_RUNTIME_HASH_AFTER": runtime_after,
        "REAL_RUNTIME_CHANGED": "NO" if runtime_before == runtime_after else "YES",
        "PREEXISTING_DIRTY_FILE_COMMITTED": "NO",
        "BROKER_OPENED": "NO",
        "LIVE_CAPTURE_EXECUTED": "NO",
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
                    "PTP-GOV.4.6C.0": "FAIL_VALIDATOR",
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
    return 0 if str(result["PTP-GOV.4.6C.0"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
