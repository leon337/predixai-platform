from __future__ import annotations

import importlib.util
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_6b1a_reconcile_display_topology.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_6b1a_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o validador da PTP-GOV.4.6B.1A")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
EDID_A = "aa" * 16


def fixture(
    outputs,
    *,
    root=(1366, 768),
    declared_count=None,
):
    query_lines = [f"Screen 0: minimum 320 x 200, current {root[0]} x {root[1]}, maximum 8192 x 8192"]
    verbose_lines = list(query_lines)
    active_lines = []
    active_outputs = [output for output in outputs if output.get("geometry")]
    for output in outputs:
        name = output["name"]
        connected = output.get("connected", True)
        geometry = output.get("geometry")
        state = "connected" if connected else "disconnected"
        geometry_text = f" {geometry}" if geometry else ""
        primary = " primary" if output.get("primary") else ""
        physical = " 300mm x 200mm" if output.get("edid") else " 0mm x 0mm"
        query_lines.append(f"{name} {state}{primary}{geometry_text} (normal left inverted right x axis y axis){physical}")
        if geometry:
            mode = geometry.split("+")[0]
            query_lines.append(f"   {mode}      60.00*+")
        verbose_lines.append(f"{name} {state}{primary}{geometry_text} (0x45) normal (normal left inverted right x axis y axis){physical}")
        verbose_lines.append(f"\tCRTC:       {output.get('crtc', 0)}")
        transform = output.get("transform", IDENTITY)
        verbose_lines.append("\tTransform:  " + " ".join(f"{value:.6f}" for value in transform[0]))
        verbose_lines.append("\t            " + " ".join(f"{value:.6f}" for value in transform[1]))
        verbose_lines.append("\t            " + " ".join(f"{value:.6f}" for value in transform[2]))
        verbose_lines.append("\t           filter:")
        if output.get("panning") is not None:
            verbose_lines.append(f"\tPanning: {output['panning']}")
        if output.get("edid"):
            verbose_lines.extend(("\tEDID:", f"\t\t{output['edid']}"))
    for index, output in enumerate(active_outputs):
        width, height, x, y = map(int, __import__("re").fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", output["geometry"]).groups())
        flags = "+" + output["name"] if output.get("primary") else output["name"]
        active_lines.append(f" {index}: {flags} {width}/300x{height}/200+{x}+{y}  {output['name']}")
    count = len(active_outputs) if declared_count is None else declared_count
    active_text = "\n".join((f"Monitors: {count}", *active_lines)) + "\n"
    return "\n".join(query_lines) + "\n", "\n".join(verbose_lines) + "\n", active_text


def derive(*args, **kwargs):
    query, verbose, active = fixture(*args, **kwargs)
    return VALIDATOR.derive_topology(query, verbose, active)


def valid_capture_report() -> str:
    return "\n".join(
        f"{key}={value}" for key, value in VALIDATOR.REQUIRED_CAPTURE_EVIDENCE.items()
    ) + "\n"


def evidence_runner(
    report: str,
    *,
    commit_returncode: int = 0,
    ancestor_returncode: int = 0,
    show_returncode: int = 0,
    blob_returncode: int = 0,
    blob: str = "synthetic-git-blob",
):
    def run(arguments, cwd):
        del cwd
        command = tuple(arguments)
        if command[0] == "cat-file":
            return subprocess.CompletedProcess(command, commit_returncode, "", "missing commit")
        if command[0] == "merge-base":
            return subprocess.CompletedProcess(command, ancestor_returncode, "", "not ancestor")
        if command[0] == "show":
            return subprocess.CompletedProcess(command, show_returncode, report if not show_returncode else "", "missing report")
        if command[0] == "rev-parse":
            return subprocess.CompletedProcess(command, blob_returncode, blob + "\n" if not blob_returncode else "", "missing blob")
        raise AssertionError(f"unexpected git command: {command!r}")
    return run


def verify_evidence_fixture(report: str, **runner_options):
    blob = runner_options.get("blob", "synthetic-git-blob")
    return VALIDATOR.verify_capture_isolation_evidence(
        git_runner=evidence_runner(report, **runner_options),
        expected_report_sha256=hashlib.sha256(report.encode("utf-8")).hexdigest(),
        expected_report_blob=blob,
    )


class PtpGov46B1ADisplayTopologyTests(unittest.TestCase):
    def test_one_active_output_derives_single_logical_surface(self) -> None:
        result = derive([{"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A}])
        self.assertEqual(result["ACTIVE_OUTPUT_COUNT"], 1)
        self.assertEqual(result["LOGICAL_DESKTOP_COUNT"], 1)
        self.assertEqual(result["CAPTURE_SURFACE_COUNT"], 1)
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "SINGLE_ACTIVE_OUTPUT")

    def test_two_mirrored_outputs_same_resolution_are_one_capture_surface(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "HDMI-1", "geometry": "1366x768+0+0", "edid": "11" * 16, "crtc": 1},
        ])
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "MIRRORED_OR_CLONED")
        self.assertEqual(result["CLONE_RESOLUTION_MODE"], "SAME")
        self.assertEqual(result["CAPTURE_SURFACE_COUNT"], 1)
        self.assertEqual(result["NON_COMMON_OUTPUT_AREA"], 0)

    def test_two_mirrored_outputs_different_resolution_derive_nested_common_area(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+0+0", "crtc": 2},
        ])
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "MIRRORED_OR_CLONED")
        self.assertEqual(result["CLONE_RESOLUTION_MODE"], "DIFFERENT")
        self.assertEqual(result["OUTPUT_GEOMETRY_INTERSECTION"], "1024x768+0+0")
        self.assertEqual(result["NON_COMMON_OUTPUT_AREA"], (1366 - 1024) * 768)
        self.assertEqual(result["TOPOLOGY_GATE_PASS"], "YES")

    def test_horizontal_extended_desktop_is_not_a_clone(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "HDMI-1", "geometry": "1024x768+1366+0", "edid": "22" * 16, "crtc": 1},
        ], root=(2390, 768))
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "EXTENDED_DESKTOP")
        self.assertEqual(result["EXTENDED_DESKTOP"], "YES")
        self.assertEqual(result["CAPTURE_SURFACE_COUNT"], 2)

    def test_vertical_extended_desktop_is_not_a_clone(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "HDMI-1", "geometry": "1366x768+0+768", "edid": "33" * 16, "crtc": 1},
        ], root=(1366, 1536))
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "EXTENDED_DESKTOP")
        self.assertEqual(result["ALL_ACTIVE_OUTPUTS_SHARE_ORIGIN"], "NO")

    def test_connected_but_inactive_output_is_not_counted_as_active_surface(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "HDMI-1", "geometry": None, "edid": "44" * 16},
        ])
        self.assertEqual(result["CONNECTED_OUTPUT_COUNT"], 2)
        self.assertEqual(result["ACTIVE_OUTPUT_COUNT"], 1)
        self.assertEqual(result["CAPTURE_SURFACE_COUNT"], 1)

    def test_active_provider_named_output_without_edid_is_classified_virtual_or_ghost(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+0+0", "crtc": 2},
        ])
        self.assertEqual(result["EDID_BACKED_OUTPUT_COUNT"], 1)
        self.assertEqual(result["VIRTUAL_OR_GHOST_OUTPUT_COUNT"], 1)
        self.assertEqual(result["VIRTUAL_OR_GHOST_OUTPUTS"], ("VGA-1-1",))

    def test_transform_or_panning_forces_inconclusive_fail_closed(self) -> None:
        transformed = ((1.2, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+0+0", "transform": transformed, "panning": "1024x768+0+0"},
        ])
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "INCONCLUSIVE")
        self.assertIn("NON_IDENTITY_TRANSFORM", result["CONTRADICTIONS"])
        self.assertIn("PANNING_DECLARED", result["CONTRADICTIONS"])
        self.assertEqual(result["TOPOLOGY_GATE_PASS"], "NO")

    def test_output_shifted_from_origin_is_extended(self) -> None:
        result = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+100+0", "crtc": 2},
        ], root=(1366, 768))
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "EXTENDED_DESKTOP")
        self.assertEqual(result["ALL_ACTIVE_OUTPUTS_SHARE_ORIGIN"], "NO")

    def test_incomplete_or_contradictory_monitor_count_forces_inconclusive(self) -> None:
        result = derive(
            [{"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A}],
            declared_count=2,
        )
        self.assertEqual(result["OUTPUT_LAYOUT_MODE"], "INCONCLUSIVE")
        self.assertIn("ACTIVE_OUTPUT_COUNT_CONTRADICTS_LISTACTIVEMONITORS", result["CONTRADICTIONS"])

    def test_edid_is_reduced_to_availability_hash_and_distinct_count(self) -> None:
        result = derive([{"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A}])
        self.assertEqual(result["EDID_AVAILABLE"]["LVDS-1"], "YES")
        self.assertEqual(len(result["EDID_SHA256"]["LVDS-1"]), 64)
        self.assertEqual(result["EDID_DISTINCT_PHYSICAL_CANDIDATE_COUNT"], 1)
        self.assertEqual(result["PHYSICAL_DISPLAY_COUNT_CONFIRMED"], "NO")
        self.assertEqual(result["PHYSICAL_DISPLAY_COUNT_INFORMATIONAL_ONLY"], "YES")
        self.assertNotIn(EDID_A, str(result))

    def test_topology_hash_is_stable_and_changes_with_spatial_layout(self) -> None:
        mirrored = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+0+0", "crtc": 2},
        ])
        shifted = derive([
            {"name": "LVDS-1", "geometry": "1366x768+0+0", "edid": EDID_A},
            {"name": "VGA-1-1", "geometry": "1024x768+100+0", "crtc": 2},
        ])
        self.assertEqual(VALIDATOR.canonical_topology_hash(mirrored), VALIDATOR.canonical_topology_hash(dict(mirrored)))
        self.assertNotEqual(VALIDATOR.canonical_topology_hash(mirrored), VALIDATOR.canonical_topology_hash(shifted))

    def test_only_four_approved_read_only_xrandr_commands_are_allowlisted(self) -> None:
        self.assertEqual(
            VALIDATOR.APPROVED_COMMANDS,
            (("xrandr", "--query"), ("xrandr", "--current"), ("xrandr", "--listactivemonitors"), ("xrandr", "--verbose")),
        )
        with self.assertRaises(ValueError):
            VALIDATOR.run_approved_command(("xrandr", "--output", "VGA-1-1", "--off"))

    def test_capture_evidence_valid_commit_and_valid_report_passes(self) -> None:
        report = valid_capture_report()
        result = verify_evidence_fixture(report)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "PASS")
        self.assertEqual(result["HARDCODED_ISOLATION_EVIDENCE"], "NO")
        self.assertEqual(result["CAPTURE_EVIDENCE_SOURCE"], "GIT_COMMIT_BLOB_ONLY")

    def test_capture_evidence_nonexistent_commit_fails_closed(self) -> None:
        result = verify_evidence_fixture(valid_capture_report(), commit_returncode=128)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("EXPECTED_COMMIT_NOT_FOUND", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_commit_not_ancestor_fails_closed(self) -> None:
        result = verify_evidence_fixture(valid_capture_report(), ancestor_returncode=1)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("EXPECTED_COMMIT_NOT_ANCESTOR_OF_HEAD", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_report_absent_from_commit_fails_closed(self) -> None:
        result = verify_evidence_fixture(valid_capture_report(), show_returncode=128)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("REPORT_NOT_FOUND_IN_EXPECTED_COMMIT", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_missing_required_field_fails_closed(self) -> None:
        report = valid_capture_report().replace("OVERLAY_SIGNATURE_PRESENT=NO\n", "")
        result = verify_evidence_fixture(report)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("REQUIRED_FIELD_MISSING:OVERLAY_SIGNATURE_PRESENT", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_divergent_value_fails_closed(self) -> None:
        report = valid_capture_report().replace(
            "AUTHORIZED_SIGNATURE_COMPLETE=YES", "AUTHORIZED_SIGNATURE_COMPLETE=NO"
        )
        result = verify_evidence_fixture(report)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("REQUIRED_VALUE_MISMATCH:AUTHORIZED_SIGNATURE_COMPLETE", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_contradictory_duplicate_key_fails_closed(self) -> None:
        report = valid_capture_report() + "REAL_RUNTIME_CHANGED=YES\n"
        result = verify_evidence_fixture(report)
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "NOT_CONFIRMED")
        self.assertIn("CONTRADICTORY_DUPLICATE_KEY:REAL_RUNTIME_CHANGED", result["CAPTURE_EVIDENCE_ERRORS"])

    def test_capture_evidence_ignores_working_tree_and_uses_git_blob_only(self) -> None:
        report = valid_capture_report()
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            working_report = repo / VALIDATOR.CAPTURE_CHARACTERIZATION_REPORT
            working_report.parent.mkdir(parents=True)
            working_report.write_text("BACKEND_XWD_EXPLICIT_CLIENT_ISOLATION=FAIL\n", encoding="utf-8")
            result = VALIDATOR.verify_capture_isolation_evidence(
                repo_root=repo,
                git_runner=evidence_runner(report),
                expected_report_sha256=hashlib.sha256(report.encode("utf-8")).hexdigest(),
                expected_report_blob="synthetic-git-blob",
            )
        self.assertEqual(result["EXPLICIT_WINDOW_ID_CAPTURE_ISOLATION"], "PASS")
        self.assertEqual(result["WORKING_TREE_CAPTURE_REPORT_USED"], "NO")


if __name__ == "__main__":
    unittest.main()
