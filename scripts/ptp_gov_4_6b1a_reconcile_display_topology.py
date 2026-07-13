#!/usr/bin/env python3
"""PTP-GOV.4.6B.1A: reconcile X11 display topology from read-only metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Compatibility re-exports are intentional: the governance validator and its approved
# tests keep their public names while production owns the sole parser implementation.
from predixai.capture.x11_display_topology import (  # noqa: E402
    APPROVED_COMMANDS,
    IDENTITY_TRANSFORM,
    X11DisplayTopologyInspector,
    canonical_topology_hash,
    connected_component_count,
    derive_topology,
    geometry_text,
    parse_active_monitors,
    parse_geometry,
    parse_query,
    parse_verbose,
    rectangle_area,
    rectangle_intersection,
    rectangle_union_bounds,
    run_approved_command,
)


PTP_ID = "PTP-GOV.4.6B.1A"
EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT = "59c1c7f5d394d7f439c724a54fc4474744e348a1"
CAPTURE_CHARACTERIZATION_REPORT = (
    "reports/20260713_PTP-GOV.4.6B.1_caracterizacao_captura_x11_AUDIT.txt"
)
EXPECTED_CAPTURE_REPORT_GIT_BLOB = "ff374a391375c9947ff30702988e4f364a59c11b"
EXPECTED_CAPTURE_REPORT_SHA256 = "9634c589204776738254b53d5d47d8b9a20ee600bfc9e1865540a51c44172fab"
REQUIRED_CAPTURE_EVIDENCE = {
    "PTP-GOV.4.6B.1": "BLOCKED_SINGLE_MONITOR_CONTRACT_VIOLATED",
    "BACKEND_XWD_EXPLICIT_CLIENT_ISOLATION": "PASS",
    "BACKEND_TECHNICAL_CAPTURE_RESULT": "ISOLATED_PIXELS_CONFIRMED",
    "OVERLAY_SIGNATURE_PRESENT": "NO",
    "AUTHORIZED_SIGNATURE_COMPLETE": "YES",
    "EXTERNAL_PIXEL_SIGNATURE_PRESENT": "NO",
    "REAL_RUNTIME_CHANGED": "NO",
}
CONTRACT_PATH = ROOT / "docs" / "contracts" / "PTP-GOV.4.6A_AUTHORIZED_WINDOW_CONTRACT.md"
REQUIRED_CONTRACT_LINES = (
    "SINGLE_LOGICAL_CAPTURE_SURFACE_REQUIRED=YES",
    "LOGICAL_DESKTOP_COUNT=REQUIRED_1",
    "CAPTURE_SURFACE_COUNT=REQUIRED_1",
    "EXTENDED_DESKTOP=REQUIRED_NO",
    "OUTPUTS_DO_NOT_EXPAND_ROOT_DESKTOP=REQUIRED_YES",
    "PANNING=REQUIRED_NONE",
    "TRANSFORM=REQUIRED_IDENTITY",
    "DISPLAY_TOPOLOGY_STABLE=REQUIRED_YES",
    "EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION=REQUIRED_PASS",
    "DISPLAY_TOPOLOGY_REVALIDATION_BEFORE_CAPTURE=REQUIRED",
    "DISPLAY_TOPOLOGY_REVALIDATION_AFTER_CAPTURE=REQUIRED",
    "FAIL_CLOSED_ON_INCONCLUSIVE_TOPOLOGY=YES",
    "CONNECTED_OUTPUT_COUNT=INFORMATIONAL",
    "ACTIVE_OUTPUT_COUNT=INFORMATIONAL",
    "EDID_BACKED_OUTPUT_COUNT=INFORMATIONAL",
    "EDID_DISTINCT_PHYSICAL_CANDIDATE_COUNT=INFORMATIONAL",
    "PHYSICAL_DISPLAY_COUNT_CONFIRMED=NO",
    "PHYSICAL_DISPLAY_COUNT_INFORMATIONAL_ONLY=YES",
)


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"MISSING")
        return digest.hexdigest()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with item.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def run_approved_git_read(
    arguments: Sequence[str], cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    args = tuple(arguments)
    expected_commit_object = f"{EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT}^{{commit}}"
    expected_report_object = (
        f"{EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT}:{CAPTURE_CHARACTERIZATION_REPORT}"
    )
    allowed = {
        ("cat-file", "-e", expected_commit_object),
        ("merge-base", "--is-ancestor", EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT, "HEAD"),
        ("show", expected_report_object),
        ("rev-parse", expected_report_object),
    }
    if args not in allowed:
        raise ValueError(f"git read is not allowlisted: {args!r}")
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=5.0,
    )


def parse_exact_key_values(text: str) -> dict[str, tuple[str, ...]]:
    values: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Z0-9][A-Z0-9._-]*)=(.*)", line)
        if match:
            values.setdefault(match.group(1), []).append(match.group(2))
    return {key: tuple(items) for key, items in values.items()}


def verify_capture_isolation_evidence(
    *,
    repo_root: Path = ROOT,
    git_runner: Callable[
        [Sequence[str], Path], subprocess.CompletedProcess[str]
    ] = run_approved_git_read,
    expected_report_sha256: str = EXPECTED_CAPTURE_REPORT_SHA256,
    expected_report_blob: str = EXPECTED_CAPTURE_REPORT_GIT_BLOB,
) -> dict[str, Any]:
    """Verify only the immutable report blob bound to the expected Git commit."""
    errors: list[str] = []
    source = "GIT_COMMIT_BLOB_ONLY"
    commit_object = f"{EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT}^{{commit}}"
    report_object = f"{EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT}:{CAPTURE_CHARACTERIZATION_REPORT}"

    commit_check = git_runner(("cat-file", "-e", commit_object), repo_root)
    if commit_check.returncode != 0:
        errors.append("EXPECTED_COMMIT_NOT_FOUND")
    ancestor_check = None
    if not errors:
        ancestor_check = git_runner(
            ("merge-base", "--is-ancestor", EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT, "HEAD"),
            repo_root,
        )
        if ancestor_check.returncode != 0:
            errors.append("EXPECTED_COMMIT_NOT_ANCESTOR_OF_HEAD")

    report_text = ""
    report_blob = ""
    report_sha256 = ""
    if not errors:
        show = git_runner(("show", report_object), repo_root)
        if show.returncode != 0:
            errors.append("REPORT_NOT_FOUND_IN_EXPECTED_COMMIT")
        else:
            report_text = show.stdout
        blob = git_runner(("rev-parse", report_object), repo_root)
        if blob.returncode != 0:
            errors.append("REPORT_BLOB_ID_NOT_AVAILABLE")
        else:
            report_blob = blob.stdout.strip()

    if report_text:
        report_sha256 = hashlib.sha256(report_text.encode("utf-8")).hexdigest()
        if report_sha256 != expected_report_sha256:
            errors.append("REPORT_SHA256_MISMATCH")
        if report_blob != expected_report_blob:
            errors.append("REPORT_GIT_BLOB_MISMATCH")
        parsed = parse_exact_key_values(report_text)
        for key, expected in REQUIRED_CAPTURE_EVIDENCE.items():
            observed = parsed.get(key, ())
            if not observed:
                errors.append(f"REQUIRED_FIELD_MISSING:{key}")
                continue
            distinct = tuple(dict.fromkeys(observed))
            if len(distinct) > 1:
                errors.append(f"CONTRADICTORY_DUPLICATE_KEY:{key}")
            elif distinct[0] != expected:
                errors.append(f"REQUIRED_VALUE_MISMATCH:{key}")

    confirmed = not errors
    return {
        "EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT": EXPECTED_CAPTURE_CHARACTERIZATION_COMMIT,
        "CAPTURE_EVIDENCE_SOURCE": source,
        "CAPTURE_EVIDENCE_COMMIT_PRESENT": "YES" if commit_check.returncode == 0 else "NO",
        "CAPTURE_EVIDENCE_COMMIT_ANCESTOR": (
            "YES"
            if ancestor_check is not None and ancestor_check.returncode == 0
            else "NO"
        ),
        "CAPTURE_EVIDENCE_REPORT_PATH": CAPTURE_CHARACTERIZATION_REPORT,
        "CAPTURE_EVIDENCE_REPORT_GIT_BLOB": report_blob or "NOT_AVAILABLE",
        "CAPTURE_EVIDENCE_REPORT_SHA256": report_sha256 or "NOT_AVAILABLE",
        "CAPTURE_EVIDENCE_REQUIRED_FIELD_COUNT": len(REQUIRED_CAPTURE_EVIDENCE),
        "CAPTURE_EVIDENCE_ERRORS": tuple(errors),
        "EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION": "PASS" if confirmed else "NOT_CONFIRMED",
        "HARDCODED_ISOLATION_EVIDENCE": "NO",
        "WORKING_TREE_CAPTURE_REPORT_USED": "NO",
    }


def verify_contract_updated(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {
            "CONTRACT_UPDATED": "NO",
            "CONTRACT_VALIDATION_ERRORS": ("CONTRACT_MISSING",),
        }
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if re.search(r"(?m)^MONITOR_COUNT=1$", text):
        errors.append("ISOLATED_MONITOR_COUNT_GATE_STILL_PRESENT")
    for required in REQUIRED_CONTRACT_LINES:
        count = text.splitlines().count(required)
        if count == 0:
            errors.append(f"CONTRACT_LINE_MISSING:{required}")
        elif count > 1:
            errors.append(f"CONTRACT_LINE_DUPLICATED:{required}")
    return {
        "CONTRACT_UPDATED": "YES" if not errors else "NO",
        "CONTRACT_VALIDATION_ERRORS": tuple(errors),
        "CONTRACT_PATH": str(path.relative_to(ROOT)),
    }


def read_snapshot() -> dict[str, Any]:
    """Compatibility wrapper backed by the functional topology inspector."""
    return X11DisplayTopologyInspector().read_snapshot().to_legacy_dict()


def execute_audit() -> dict[str, Any]:
    if str(os.environ.get("XDG_SESSION_TYPE") or "").lower() != "x11":
        raise RuntimeError("DISPLAY_SERVER_NOT_X11")
    missing = tuple(
        command[0] for command in APPROVED_COMMANDS if shutil.which(command[0]) is None
    )
    if missing:
        raise RuntimeError(f"MISSING_TOOLS:{','.join(missing)}")
    runtime_path = ROOT / "data" / "runtime"
    runtime_before = hash_tree(runtime_path)
    before = read_snapshot()
    time.sleep(0.05)
    after = read_snapshot()
    runtime_after = hash_tree(runtime_path)
    changed = before["HASH"] != after["HASH"]
    topology = dict(after["TOPOLOGY"])
    capture_evidence = verify_capture_isolation_evidence()
    contract_evidence = verify_contract_updated()
    runtime_unchanged = runtime_before == runtime_after
    conditions_pass = (
        topology["TOPOLOGY_GATE_PASS"] == "YES"
        and topology["LOGICAL_DESKTOP_COUNT"] == 1
        and topology["CAPTURE_SURFACE_COUNT"] == 1
        and topology["OUTPUT_LAYOUT_MODE"] == "MIRRORED_OR_CLONED"
        and topology["ALL_ACTIVE_OUTPUTS_SHARE_ORIGIN"] == "YES"
        and topology["OUTPUTS_DO_NOT_EXPAND_ROOT_DESKTOP"] == "YES"
        and topology["EXTENDED_DESKTOP"] == "NO"
        and not changed
        and capture_evidence["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"] == "PASS"
        and capture_evidence["HARDCODED_ISOLATION_EVIDENCE"] == "NO"
        and contract_evidence["CONTRACT_UPDATED"] == "YES"
        and runtime_unchanged
    )
    if changed:
        topology["OUTPUT_LAYOUT_MODE"] = "INCONCLUSIVE"
    status = (
        "PASS_DISPLAY_TOPOLOGY_MIRRORED_OR_CLONED"
        if conditions_pass
        else "BLOCKED_DISPLAY_TOPOLOGY"
    )
    return {
        "PTP": PTP_ID,
        "EXECUTION_STATUS": status,
        **topology,
        "DISPLAY_TOPOLOGY_HASH_BEFORE": before["HASH"],
        "DISPLAY_TOPOLOGY_HASH_AFTER": after["HASH"],
        "DISPLAY_TOPOLOGY_CHANGED_DURING_AUDIT": "YES" if changed else "NO",
        **capture_evidence,
        **contract_evidence,
        "FAIL_CLOSED": "NO" if conditions_pass else "YES",
        "PTP-GOV.4.6B.2_BLOCKED": "NO" if conditions_pass else "YES",
        "CONTRACT_CHANGE_APPLIED": (
            "YES" if contract_evidence["CONTRACT_UPDATED"] == "YES" else "NO"
        ),
        "PTP-GOV.4.6B.2_STARTED": "NO",
        "CAPTURE_FUNCTIONAL_IMPLEMENTATION_STARTED": "NO",
        "XRANDR_COMMANDS_EXECUTED": tuple(
            " ".join(command) for command in APPROVED_COMMANDS
        ),
        "XRANDR_MUTATION_COMMAND_EXECUTED": "NO",
        "BROKER_OPENED": "NO",
        "CAPTURE_EXECUTED": "NO",
        "OCR_EXECUTED": "NO",
        "TESSERACT_EXECUTED": "NO",
        "SERVER_STARTED": "NO",
        "MOBILE_V2_STARTED": "NO",
        "OBSERVER_STARTED": "NO",
        "NETWORK_EXTERNAL": "NO",
        "REAL_RUNTIME_HASH_BEFORE": runtime_before,
        "REAL_RUNTIME_HASH_AFTER": runtime_after,
        "REAL_RUNTIME_CHANGED": "NO" if runtime_unchanged else "YES",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)
    try:
        result = execute_audit()
    except Exception as exc:
        result = {
            "PTP": PTP_ID,
            "EXECUTION_STATUS": "BLOCKED_VALIDATOR_ERROR",
            "VALIDATOR_ERROR": f"{type(exc).__name__}: {exc}",
            "FAIL_CLOSED": "YES",
            "CONTRACT_CHANGE_APPLIED": "NO",
            "PTP-GOV.4.6B.2_BLOCKED": "YES",
            "PTP-GOV.4.6B.2_STARTED": "NO",
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output_json:
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return (
        0
        if result["EXECUTION_STATUS"] == "PASS_DISPLAY_TOPOLOGY_MIRRORED_OR_CLONED"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
