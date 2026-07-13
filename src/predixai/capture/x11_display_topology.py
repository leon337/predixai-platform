"""Read-only X11 display topology inspection for controlled capture."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


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


def run_approved_command(command: Sequence[str]) -> str:
    """Run one of the four read-only xrandr metadata commands."""
    command_tuple = tuple(command)
    if command_tuple not in APPROVED_COMMANDS:
        raise ValueError(f"xrandr command is not allowlisted: {command_tuple!r}")
    completed = subprocess.run(
        list(command_tuple),
        check=False,
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command_tuple)} failed with "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    return completed.stdout


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
    screen_match = re.search(
        r"^Screen\s+(\d+):.*?current\s+(\d+)\s+x\s+(\d+)",
        text,
        re.MULTILINE,
    )
    screens = tuple(re.findall(r"^Screen\s+(\d+):", text, re.MULTILINE))
    outputs: dict[str, dict[str, Any]] = {}
    output_pattern = re.compile(
        r"^(\S+)\s+(connected|disconnected)(?:\s+primary)?"
        r"(?:\s+(\d+x\d+\+-?\d+\+-?\d+))?\s*(.*)$"
    )
    current_output: str | None = None
    for line in text.splitlines():
        match = output_pattern.match(line)
        if match:
            name, connection, raw_geometry, remainder = match.groups()
            primary = bool(
                re.search(rf"^{re.escape(name)}\s+connected\s+primary\b", line)
            )
            physical_match = re.search(r"(\d+)mm\s+x\s+(\d+)mm", remainder)
            outputs[name] = {
                "NAME": name,
                "CONNECTED": connection == "connected",
                "ACTIVE": bool(raw_geometry),
                "GEOMETRY": parse_geometry(raw_geometry) if raw_geometry else None,
                "PRIMARY": primary,
                "PHYSICAL_MM": (
                    {
                        "width": int(physical_match.group(1)),
                        "height": int(physical_match.group(2)),
                    }
                    if physical_match
                    else None
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
    headers = re.compile(
        r"^(\S+)\s+(connected|disconnected)(?:\s+primary)?"
        r"(?:\s+(\d+x\d+\+-?\d+\+-?\d+))?.*$"
    )
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
                    "PROVIDER_NAMED_OUTPUT"
                    if re.search(r"-\d+-\d+$", name)
                    else "NOT_DECLARED"
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
                candidates = [stripped.partition(":")[2].strip()]
                if index + 2 < len(lines):
                    candidates.extend(
                        (lines[index + 1].strip(), lines[index + 2].strip())
                    )
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
            r"^\s*\d+:\s+([^\s]+)\s+(\d+)(?:/\d+)?x(\d+)(?:/\d+)?"
            r"\+(-?\d+)\+(-?\d+)\s+(\S+)",
            line,
        )
        if match:
            flags_name, width, height, x, y, output_name = match.groups()
            monitors.append(
                {
                    "OUTPUT": output_name,
                    "FLAGS": flags_name,
                    "GEOMETRY": {
                        "x": int(x),
                        "y": int(y),
                        "width": int(width),
                        "height": int(height),
                    },
                }
            )
    return {
        "DECLARED_COUNT": int(count_match.group(1)) if count_match else None,
        "MONITORS": monitors,
    }


def rectangle_union_bounds(
    rectangles: Sequence[Mapping[str, int]],
) -> dict[str, int] | None:
    if not rectangles:
        return None
    left = min(rectangle["x"] for rectangle in rectangles)
    top = min(rectangle["y"] for rectangle in rectangles)
    right = max(rectangle["x"] + rectangle["width"] for rectangle in rectangles)
    bottom = max(rectangle["y"] + rectangle["height"] for rectangle in rectangles)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def rectangle_intersection(
    rectangles: Sequence[Mapping[str, int]],
) -> dict[str, int] | None:
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


def _overlap_or_touch(
    first: Mapping[str, int], second: Mapping[str, int]
) -> bool:
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
    return all(
        abs(float(value[row][column]) - IDENTITY_TRANSFORM[row][column]) < 1e-6
        for row in range(3)
        for column in range(3)
    )


def derive_topology(
    query_text: str, verbose_text: str, active_text: str
) -> dict[str, Any]:
    query = parse_query(query_text)
    verbose = parse_verbose(verbose_text)
    active_monitors = parse_active_monitors(active_text)
    root_geometry = query["ROOT_GEOMETRY"]
    outputs = query["OUTPUTS"]
    connected = [output for output in outputs.values() if output["CONNECTED"]]
    active = [
        output
        for output in connected
        if output["ACTIVE"] and output["GEOMETRY"]
    ]
    rectangles = [output["GEOMETRY"] for output in active]
    union = rectangle_union_bounds(rectangles)
    intersection = rectangle_intersection(rectangles)
    all_share_origin = bool(rectangles) and len(
        {(item["x"], item["y"]) for item in rectangles}
    ) == 1
    same_resolution = len(
        {(item["width"], item["height"]) for item in rectangles}
    ) <= 1
    union_matches_root = bool(union and root_geometry and union == root_geometry)
    logical_desktop_count = connected_component_count(rectangles)

    active_verbose = [verbose.get(output["NAME"], {}) for output in active]
    missing_verbose = any(not value for value in active_verbose)
    transforms = {
        output["NAME"]: verbose.get(output["NAME"], {}).get("TRANSFORM")
        for output in active
    }
    panning = {
        output["NAME"]: verbose.get(output["NAME"], {}).get("PANNING")
        for output in active
    }
    crtc = {
        output["NAME"]: verbose.get(output["NAME"], {}).get("CRTC")
        for output in active
    }
    provider = {
        output["NAME"]: verbose.get(output["NAME"], {}).get(
            "PROVIDER_RELATION", "NOT_DECLARED"
        )
        for output in active
    }
    transform_inconclusive = missing_verbose or any(
        value is None for value in transforms.values()
    )
    non_identity_transform = any(
        value is not None and not _identity_transform(value)
        for value in transforms.values()
    )
    panning_declared = any(
        value not in {None, "", "0x0+0+0"} for value in panning.values()
    )

    edid_hashes: dict[str, str] = {}
    edid_available: dict[str, str] = {}
    virtual_or_ghost: list[str] = []
    for output in connected:
        verbose_output = verbose.get(output["NAME"], {})
        edid = str(verbose_output.get("EDID_HEX") or "")
        edid_available[output["NAME"]] = "YES" if edid else "NO"
        if edid:
            edid_hashes[output["NAME"]] = hashlib.sha256(
                bytes.fromhex(edid)
            ).hexdigest()
        physical = output.get("PHYSICAL_MM") or {}
        zero_physical_size = (
            physical.get("width") == 0 and physical.get("height") == 0
        )
        provider_named = (
            verbose_output.get("PROVIDER_RELATION") == "PROVIDER_NAMED_OUTPUT"
        )
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

    capture_surface_count = (
        1 if layout in {"MIRRORED_OR_CLONED", "SINGLE_ACTIVE_OUTPUT"} else len(active)
    )
    common_area = rectangle_area(intersection)
    union_area = rectangle_area(union)
    primary = next(
        (output["NAME"] for output in active if output["PRIMARY"]),
        "NONE_DECLARED",
    )
    pass_gate = (
        logical_desktop_count == 1
        and capture_surface_count == 1
        and layout == "MIRRORED_OR_CLONED"
        and all_share_origin
        and union_matches_root
        and not extended
    )
    return {
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
        "TRANSFORM": {
            name: "IDENTITY" if _identity_transform(value) else "NON_IDENTITY_OR_UNKNOWN"
            for name, value in transforms.items()
        },
        "PANNING": {
            name: value or "NONE_DECLARED" for name, value in panning.items()
        },
        "PRIMARY_OUTPUT": primary,
        "ROTATION": {output["NAME"]: output["ROTATION"] for output in active},
        "REFLECTION": {output["NAME"]: output["REFLECTION"] for output in active},
        "CURRENT_MODE": {
            output["NAME"]: output["CURRENT_MODE"] for output in active
        },
        "OUTPUT_POSITION": {
            output["NAME"]: geometry_text(output["GEOMETRY"]) for output in active
        },
        "PROVIDER_RELATION": provider,
        "EDID_AVAILABLE": edid_available,
        "EDID_SHA256": edid_hashes,
        "CONTRADICTIONS": tuple(contradictions),
        "TOPOLOGY_GATE_PASS": "YES" if pass_gate else "NO",
    }


def canonical_topology_hash(topology: Mapping[str, Any]) -> str:
    material = json.dumps(
        topology,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_thaw(item) for item in value)
    return value


@dataclass(frozen=True)
class X11DisplayTopology:
    """One immutable, canonical X11 topology observation."""

    values: Mapping[str, Any]
    topology_hash: str

    @classmethod
    def from_values(cls, values: Mapping[str, Any]) -> "X11DisplayTopology":
        material = _thaw(values)
        return cls(
            values=_freeze(material),
            topology_hash=canonical_topology_hash(material),
        )

    @property
    def gate_pass(self) -> bool:
        return self.values.get("TOPOLOGY_GATE_PASS") == "YES"

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.values)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {"TOPOLOGY": self.to_dict(), "HASH": self.topology_hash}


CommandRunner = Callable[[Sequence[str]], str]


class X11DisplayTopologyInspector:
    """Inspect and hash X11 topology without mutating xrandr state."""

    def __init__(self, command_runner: CommandRunner = run_approved_command) -> None:
        self._command_runner = command_runner

    def read_snapshot(self) -> X11DisplayTopology:
        raw = {
            command[1]: self._command_runner(command)
            for command in APPROVED_COMMANDS
        }
        query = raw["--query"]
        current = raw["--current"]
        topology = derive_topology(
            query,
            raw["--verbose"],
            raw["--listactivemonitors"],
        )
        if parse_query(query) != parse_query(current):
            topology = dict(topology)
            topology["CONTRADICTIONS"] = tuple(
                (*topology["CONTRADICTIONS"], "QUERY_CURRENT_TOPOLOGY_MISMATCH")
            )
            topology["OUTPUT_LAYOUT_MODE"] = "INCONCLUSIVE"
            topology["TOPOLOGY_GATE_PASS"] = "NO"
        return X11DisplayTopology.from_values(topology)
