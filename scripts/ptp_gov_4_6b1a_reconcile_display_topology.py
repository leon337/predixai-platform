#!/usr/bin/env python3
"""PTP-GOV.4.6B.1A: reconcile X11 display topology from read-only xrandr metadata."""

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
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
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
APPROVED_COMMANDS = (
    ("xrandr", "--query"),
    ("xrandr", "--current"),
    ("xrandr", "--listactivemonitors"),
    ("xrandr", "--verbose"),
)
IDENTITY_TRANSFORM = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
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


def run_approved_command(command: Sequence[str]) -> str:
    command_tuple = tuple(command)
    if command_tuple not in APPROVED_COMMANDS:
        raise ValueError(f"xrandr command is not allowlisted: {command_tuple!r}")
    completed = subprocess.run(
        list(command_tuple), check=False, capture_output=True, text=True, timeout=5.0
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command_tuple)} failed with {completed.returncode}: {completed.stderr.strip()}"
        )
    return completed.stdout


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
        ["git", *args], cwd=cwd, check=False, capture_output=True, text=True, timeout=5.0
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
    git_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] = run_approved_git_read,
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
            "YES" if ancestor_check is not None and ancestor_check.returncode == 0 else "NO"
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
        return {"CONTRACT_UPDATED": "NO", "CONTRACT_VALIDATION_ERRORS": ("CONTRACT_MISSING",)}
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


def parse_geometry(value: str) -> dict[str, int] | None:
    match = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", value)
    if not match:
        return None
    width, height, x, y = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def geometry_text(geometry: Mapping[str, int] | None) -> str:
    if not geometry:
        return "UNKNOWN"
    return f'{geometry["width"]}x{geometry["height"]}+{geometry["x"]}+{geometry["y"]}'


def parse_query(text: str) -> dict[str, Any]:
    screen_match = re.search(r"^Screen\s+(\d+):.*?current\s+(\d+)\s+x\s+(\d+)", text, re.MULTILINE)
    screens = tuple(re.findall(r"^Screen\s+(\d+):", text, re.MULTILINE))
    outputs: dict[str, dict[str, Any]] = {}
    output_pattern = re.compile(
        r"^(\S+)\s+(connected|disconnected)(?:\s+primary)?(?:\s+(\d+x\d+\+-?\d+\+-?\d+))?\s*(.*)$"
    )
    current_output: str | None = None
    for line in text.splitlines():
        match = output_pattern.match(line)
        if match:
            name, connection, raw_geometry, remainder = match.groups()
            primary = bool(re.search(rf"^{re.escape(name)}\s+connected\s+primary\b", line))
            physical_match = re.search(r"(\d+)mm\s+x\s+(\d+)mm", remainder)
            outputs[name] = {
                "NAME": name,
                "CONNECTED": connection == "connected",
                "ACTIVE": bool(raw_geometry),
                "GEOMETRY": parse_geometry(raw_geometry) if raw_geometry else None,
                "PRIMARY": primary,
                "PHYSICAL_MM": (
                    {"width": int(physical_match.group(1)), "height": int(physical_match.group(2))}
                    if physical_match else None
                ),
                "CURRENT_MODE": None,
                "ROTATION": "normal" if "normal" in remainder else "UNKNOWN",
                "REFLECTION": "normal" if "normal" in remainder else "UNKNOWN",
            }
            current_output = name
            continue
        if current_output and re.match(r"^\s+\S", line) and "*" in line:
            mode_match = re.match(r"^\s+(\d+x\d+)\s+", line)
            if mode_match:
                outputs[current_output]["CURRENT_MODE"] = mode_match.group(1)
    root_geometry = None
    if screen_match:
        root_geometry = {
            "x": 0,
            "y": 0,
            "width": int(screen_match.group(2)),
            "height": int(screen_match.group(3)),
        }
    return {
        "SCREEN_IDS": screens,
        "ROOT_GEOMETRY": root_geometry,
        "OUTPUTS": outputs,
    }


def _parse_edid(lines: Sequence[str], start: int) -> tuple[str, int]:
    chunks: list[str] = []
    index = start
    while index < len(lines):
        stripped = lines[index].strip()
        if not re.fullmatch(r"[0-9a-fA-F]{32}", stripped):
            break
        chunks.append(stripped.lower())
        index += 1
    return "".join(chunks), index


def parse_verbose(text: str) -> dict[str, dict[str, Any]]:
    lines = text.splitlines()
    headers = re.compile(r"^(\S+)\s+(connected|disconnected)(?:\s+primary)?(?:\s+(\d+x\d+\+-?\d+\+-?\d+))?.*$")
    result: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        header = headers.match(line)
        if header:
            name, connection, raw_geometry = header.groups()
            current = {
                "NAME": name,
                "CONNECTED": connection == "connected",
                "ACTIVE": bool(raw_geometry),
                "CRTC": None,
                "TRANSFORM": None,
                "PANNING": None,
                "EDID_HEX": "",
                "PROVIDER_RELATION": (
                    "PROVIDER_NAMED_OUTPUT" if re.search(r"-\d+-\d+$", name) else "NOT_DECLARED"
                ),
            }
            result[name] = current
            index += 1
            continue
        if current is not None:
            stripped = line.strip()
            if stripped.startswith("CRTC:"):
                value = stripped.partition(":")[2].strip()
                current["CRTC"] = int(value) if value.isdigit() else None
            elif stripped.startswith("Transform:"):
                rows: list[tuple[float, float, float]] = []
                first = stripped.partition(":")[2].strip()
                candidates = [first]
                if index + 2 < len(lines):
                    candidates.extend((lines[index + 1].strip(), lines[index + 2].strip()))
                for candidate in candidates:
                    values = re.findall(r"-?\d+(?:\.\d+)?", candidate)
                    if len(values) >= 3:
                        rows.append(tuple(float(value) for value in values[:3]))
                current["TRANSFORM"] = tuple(rows) if len(rows) == 3 else None
                index += 2
            elif stripped.startswith("Panning"):
                current["PANNING"] = stripped.partition(":")[2].strip() or "DECLARED"
            elif stripped == "EDID:":
                edid, next_index = _parse_edid(lines, index + 1)
                current["EDID_HEX"] = edid
                index = next_index - 1
        index += 1
    return result


def parse_active_monitors(text: str) -> dict[str, Any]:
    count_match = re.search(r"^Monitors:\s*(\d+)", text, re.MULTILINE)
    monitors = []
    for line in text.splitlines():
        match = re.match(
            r"^\s*\d+:\s+([^\s]+)\s+(\d+)(?:/\d+)?x(\d+)(?:/\d+)?\+(-?\d+)\+(-?\d+)\s+(\S+)",
            line,
        )
        if match:
            flags_name, width, height, x, y, output_name = match.groups()
            monitors.append(
                {
                    "OUTPUT": output_name,
                    "FLAGS": flags_name,
                    "GEOMETRY": {
                        "x": int(x), "y": int(y), "width": int(width), "height": int(height)
                    },
                }
            )
    return {"DECLARED_COUNT": int(count_match.group(1)) if count_match else None, "MONITORS": monitors}


def rectangle_union_bounds(rectangles: Sequence[Mapping[str, int]]) -> dict[str, int] | None:
    if not rectangles:
        return None
    left = min(rectangle["x"] for rectangle in rectangles)
    top = min(rectangle["y"] for rectangle in rectangles)
    right = max(rectangle["x"] + rectangle["width"] for rectangle in rectangles)
    bottom = max(rectangle["y"] + rectangle["height"] for rectangle in rectangles)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def rectangle_intersection(rectangles: Sequence[Mapping[str, int]]) -> dict[str, int] | None:
    if not rectangles:
        return None
    left = max(rectangle["x"] for rectangle in rectangles)
    top = max(rectangle["y"] for rectangle in rectangles)
    right = min(rectangle["x"] + rectangle["width"] for rectangle in rectangles)
    bottom = min(rectangle["y"] + rectangle["height"] for rectangle in rectangles)
    if right <= left or bottom <= top:
        return None
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def rectangle_area(rectangle: Mapping[str, int] | None) -> int:
    return int(rectangle["width"] * rectangle["height"]) if rectangle else 0


def _overlap_or_touch(first: Mapping[str, int], second: Mapping[str, int]) -> bool:
    return not (
        first["x"] + first["width"] < second["x"]
        or second["x"] + second["width"] < first["x"]
        or first["y"] + first["height"] < second["y"]
        or second["y"] + second["height"] < first["y"]
    )


def connected_component_count(rectangles: Sequence[Mapping[str, int]]) -> int:
    if not rectangles:
        return 0
    unseen = set(range(len(rectangles)))
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbors = {
                candidate
                for candidate in unseen
                if _overlap_or_touch(rectangles[current], rectangles[candidate])
            }
            unseen.difference_update(neighbors)
            stack.extend(neighbors)
    return components


def _identity_transform(value: Any) -> bool:
    if value is None or len(value) != 3:
        return False
    return all(abs(float(value[row][column]) - IDENTITY_TRANSFORM[row][column]) < 1e-6 for row in range(3) for column in range(3))


def derive_topology(query_text: str, verbose_text: str, active_text: str) -> dict[str, Any]:
    query = parse_query(query_text)
    verbose = parse_verbose(verbose_text)
    active_monitors = parse_active_monitors(active_text)
    root_geometry = query["ROOT_GEOMETRY"]
    outputs = query["OUTPUTS"]
    connected = [output for output in outputs.values() if output["CONNECTED"]]
    active = [output for output in connected if output["ACTIVE"] and output["GEOMETRY"]]
    rectangles = [output["GEOMETRY"] for output in active]
    union = rectangle_union_bounds(rectangles)
    intersection = rectangle_intersection(rectangles)
    all_share_origin = bool(rectangles) and len({(item["x"], item["y"]) for item in rectangles}) == 1
    same_resolution = len({(item["width"], item["height"]) for item in rectangles}) <= 1
    union_matches_root = bool(union and root_geometry and union == root_geometry)
    logical_desktop_count = connected_component_count(rectangles)

    active_verbose = [verbose.get(output["NAME"], {}) for output in active]
    missing_verbose = any(not value for value in active_verbose)
    transforms = {output["NAME"]: verbose.get(output["NAME"], {}).get("TRANSFORM") for output in active}
    panning = {output["NAME"]: verbose.get(output["NAME"], {}).get("PANNING") for output in active}
    crtc = {output["NAME"]: verbose.get(output["NAME"], {}).get("CRTC") for output in active}
    provider = {output["NAME"]: verbose.get(output["NAME"], {}).get("PROVIDER_RELATION", "NOT_DECLARED") for output in active}
    transform_inconclusive = missing_verbose or any(value is None for value in transforms.values())
    non_identity_transform = any(value is not None and not _identity_transform(value) for value in transforms.values())
    panning_declared = any(value not in {None, "", "0x0+0+0"} for value in panning.values())

    edid_hashes: dict[str, str] = {}
    edid_available: dict[str, str] = {}
    virtual_or_ghost: list[str] = []
    for output in connected:
        verbose_output = verbose.get(output["NAME"], {})
        edid = str(verbose_output.get("EDID_HEX") or "")
        edid_available[output["NAME"]] = "YES" if edid else "NO"
        if edid:
            edid_hashes[output["NAME"]] = hashlib.sha256(bytes.fromhex(edid)).hexdigest()
        physical = output.get("PHYSICAL_MM") or {}
        zero_physical_size = physical.get("width") == 0 and physical.get("height") == 0
        provider_named = verbose_output.get("PROVIDER_RELATION") == "PROVIDER_NAMED_OUTPUT"
        if not edid and (zero_physical_size or provider_named):
            virtual_or_ghost.append(output["NAME"])

    mirrored_candidate = (
        len(active) >= 1
        and all_share_origin
        and union_matches_root
        and not panning_declared
        and not non_identity_transform
        and not transform_inconclusive
    )
    extended = bool(
        len(active) > 1
        and (
            not all_share_origin
            or not union_matches_root
            or panning_declared
            or non_identity_transform
        )
    )
    contradictions: list[str] = []
    if root_geometry is None:
        contradictions.append("ROOT_GEOMETRY_MISSING")
    if not active:
        contradictions.append("NO_ACTIVE_OUTPUT")
    if active_monitors["DECLARED_COUNT"] is None:
        contradictions.append("ACTIVE_MONITOR_COUNT_MISSING")
    elif active_monitors["DECLARED_COUNT"] != len(active):
        contradictions.append("ACTIVE_OUTPUT_COUNT_CONTRADICTS_LISTACTIVEMONITORS")
    if transform_inconclusive:
        contradictions.append("TRANSFORM_INCONCLUSIVE")
    if panning_declared:
        contradictions.append("PANNING_DECLARED")
    if non_identity_transform:
        contradictions.append("NON_IDENTITY_TRANSFORM")

    if contradictions:
        layout = "INCONCLUSIVE"
    elif mirrored_candidate and len(active) > 1:
        layout = "MIRRORED_OR_CLONED"
    elif mirrored_candidate and len(active) == 1:
        layout = "SINGLE_ACTIVE_OUTPUT"
    elif extended:
        layout = "EXTENDED_DESKTOP"
    else:
        layout = "INCONCLUSIVE"

    capture_surface_count = 1 if layout in {"MIRRORED_OR_CLONED", "SINGLE_ACTIVE_OUTPUT"} else len(active)
    common_area = rectangle_area(intersection)
    union_area = rectangle_area(union)
    primary = next((output["NAME"] for output in active if output["PRIMARY"]), "NONE_DECLARED")
    pass_gate = (
        logical_desktop_count == 1
        and capture_surface_count == 1
        and layout == "MIRRORED_OR_CLONED"
        and all_share_origin
        and union_matches_root
        and not extended
    )
    result = {
        "CONNECTED_OUTPUT_COUNT": len(connected),
        "ACTIVE_OUTPUT_COUNT": len(active),
        "EDID_BACKED_OUTPUT_COUNT": len(edid_hashes),
        "EDID_DISTINCT_PHYSICAL_CANDIDATE_COUNT": len(set(edid_hashes.values())),
        "PHYSICAL_DISPLAY_COUNT_CONFIRMED": "NO",
        "PHYSICAL_DISPLAY_COUNT_INFORMATIONAL_ONLY": "YES",
        "VIRTUAL_OR_GHOST_OUTPUT_COUNT": len(virtual_or_ghost),
        "VIRTUAL_OR_GHOST_OUTPUTS": tuple(virtual_or_ghost),
        "LOGICAL_DESKTOP_COUNT": logical_desktop_count,
        "CAPTURE_SURFACE_COUNT": capture_surface_count,
        "OUTPUT_LAYOUT_MODE": layout,
        "MIRRORED_OUTPUTS": "YES" if layout == "MIRRORED_OR_CLONED" else "NO",
        "EXTENDED_DESKTOP": "YES" if extended else "NO",
        "ROOT_GEOMETRY": geometry_text(root_geometry),
        "OUTPUT_GEOMETRY_UNION": geometry_text(union),
        "OUTPUT_GEOMETRY_INTERSECTION": geometry_text(intersection),
        "COMMON_VISIBLE_AREA": common_area,
        "NON_COMMON_OUTPUT_AREA": max(0, union_area - common_area),
        "CLONE_RESOLUTION_MODE": "SAME" if same_resolution else "DIFFERENT",
        "ALL_ACTIVE_OUTPUTS_SHARE_ORIGIN": "YES" if all_share_origin else "NO",
        "OUTPUTS_DO_NOT_EXPAND_ROOT_DESKTOP": "YES" if union_matches_root else "NO",
        "CRTC": crtc,
        "TRANSFORM": {name: "IDENTITY" if _identity_transform(value) else "NON_IDENTITY_OR_UNKNOWN" for name, value in transforms.items()},
        "PANNING": {name: value or "NONE_DECLARED" for name, value in panning.items()},
        "PRIMARY_OUTPUT": primary,
        "ROTATION": {output["NAME"]: output["ROTATION"] for output in active},
        "REFLECTION": {output["NAME"]: output["REFLECTION"] for output in active},
        "CURRENT_MODE": {output["NAME"]: output["CURRENT_MODE"] for output in active},
        "OUTPUT_POSITION": {output["NAME"]: geometry_text(output["GEOMETRY"]) for output in active},
        "PROVIDER_RELATION": provider,
        "EDID_AVAILABLE": edid_available,
        "EDID_SHA256": edid_hashes,
        "CONTRADICTIONS": tuple(contradictions),
        "TOPOLOGY_GATE_PASS": "YES" if pass_gate else "NO",
    }
    return result


def canonical_topology_hash(topology: Mapping[str, Any]) -> str:
    material = json.dumps(topology, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def read_snapshot() -> dict[str, Any]:
    raw = {command[1]: run_approved_command(command) for command in APPROVED_COMMANDS}
    query = raw["--query"]
    current = raw["--current"]
    if parse_query(query) != parse_query(current):
        contradiction = "QUERY_CURRENT_TOPOLOGY_MISMATCH"
    else:
        contradiction = "NONE"
    topology = derive_topology(query, raw["--verbose"], raw["--listactivemonitors"])
    if contradiction != "NONE":
        topology = dict(topology)
        topology["CONTRADICTIONS"] = tuple((*topology["CONTRADICTIONS"], contradiction))
        topology["OUTPUT_LAYOUT_MODE"] = "INCONCLUSIVE"
        topology["TOPOLOGY_GATE_PASS"] = "NO"
    return {"TOPOLOGY": topology, "HASH": canonical_topology_hash(topology)}


def execute_audit() -> dict[str, Any]:
    if str(os.environ.get("XDG_SESSION_TYPE") or "").lower() != "x11":
        raise RuntimeError("DISPLAY_SERVER_NOT_X11")
    missing = tuple(command[0] for command in APPROVED_COMMANDS if shutil.which(command[0]) is None)
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
    status = "PASS_DISPLAY_TOPOLOGY_MIRRORED_OR_CLONED" if conditions_pass else "BLOCKED_DISPLAY_TOPOLOGY"
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
        "CONTRACT_CHANGE_APPLIED": "YES" if contract_evidence["CONTRACT_UPDATED"] == "YES" else "NO",
        "PTP-GOV.4.6B.2_STARTED": "NO",
        "CAPTURE_FUNCTIONAL_IMPLEMENTATION_STARTED": "NO",
        "XRANDR_COMMANDS_EXECUTED": tuple(" ".join(command) for command in APPROVED_COMMANDS),
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
    return 0 if result["EXECUTION_STATUS"] == "PASS_DISPLAY_TOPOLOGY_MIRRORED_OR_CLONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
