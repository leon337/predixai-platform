from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_5_validate_mobile_v2_lan.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_5_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o validador LAN")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def route(dev: str, source: str, metric: int = 100):
    return {
        "dst": "default",
        "gateway": "192.168.10.1",
        "dev": dev,
        "prefsrc": source,
        "metric": metric,
    }


def address(dev: str, ipv4: str, *, operstate: str = "UP"):
    return {
        "ifname": dev,
        "operstate": operstate,
        "flags": ["UP", "LOWER_UP"],
        "addr_info": [
            {"family": "inet", "local": ipv4, "scope": "global"}
        ],
    }


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PtpGov45LanValidationTests(unittest.TestCase):
    def test_excluded_interfaces_cover_loopback_containers_and_vpn(self) -> None:
        for interface in (
            "lo",
            "docker0",
            "veth123",
            "virbr0",
            "br-deadbeef",
            "tun0",
            "wg0",
            "tailscale0",
        ):
            with self.subTest(interface=interface):
                self.assertTrue(VALIDATOR.is_excluded_interface(interface))
        self.assertFalse(VALIDATOR.is_excluded_interface("enp4s0"))
        self.assertFalse(VALIDATOR.is_excluded_interface("wlan0"))

    def test_only_exact_rfc1918_ranges_are_accepted(self) -> None:
        for ipv4 in ("192.168.1.10", "10.2.3.4", "172.16.0.1", "172.31.255.254"):
            self.assertTrue(VALIDATOR.is_rfc1918(ipv4))
        for ipv4 in ("127.0.0.1", "8.8.8.8", "172.15.1.1", "172.32.1.1", "169.254.1.1"):
            self.assertFalse(VALIDATOR.is_rfc1918(ipv4))

    def test_lowest_metric_active_default_route_is_selected(self) -> None:
        result = VALIDATOR.select_lan_network(
            [
                route("wlan0", "192.168.10.103", 600),
                route("enp4s0", "192.168.10.101", 100),
            ],
            [
                address("wlan0", "192.168.10.103"),
                address("enp4s0", "192.168.10.101"),
            ],
        )
        self.assertEqual(result["active_network_interface"], "enp4s0")
        self.assertEqual(result["computer_local_ipv4"], "192.168.10.101")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["mobile_v2_local_url"], "http://192.168.10.101:5001")

    def test_public_container_and_inactive_candidates_are_rejected(self) -> None:
        result = VALIDATOR.select_lan_network(
            [
                route("eth0", "203.0.113.4"),
                route("docker0", "172.17.0.1"),
                route("wlan0", "192.168.1.5"),
            ],
            [
                address("eth0", "203.0.113.4"),
                address("docker0", "172.17.0.1"),
                address("wlan0", "192.168.1.5", operstate="DOWN"),
            ],
        )
        self.assertEqual(result["local_network_detection_status"], "BLOCKED")
        self.assertEqual(result["mobile_url"], "NOT_AVAILABLE")
        self.assertTrue(result["do_not_guess_ip"])

    def test_detection_uses_only_local_ip_commands(self) -> None:
        completed = [
            subprocess.CompletedProcess([], 0, json.dumps([route("enp4s0", "10.0.0.5")]), ""),
            subprocess.CompletedProcess([], 0, json.dumps([address("enp4s0", "10.0.0.5")]), ""),
        ]
        runner = mock.Mock(side_effect=completed)
        result = VALIDATOR.detect_local_network(run_command=runner)
        self.assertEqual(result["computer_local_ipv4"], "10.0.0.5")
        commands = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(
            commands,
            [
                ["ip", "-j", "route", "show", "default"],
                ["ip", "-j", "-4", "address", "show"],
            ],
        )

    def test_detection_failure_blocks_without_guessing(self) -> None:
        failed = subprocess.CompletedProcess([], 1, "", "netlink blocked")
        result = VALIDATOR.detect_local_network(run_command=mock.Mock(return_value=failed))
        self.assertEqual(result["local_network_detection_status"], "BLOCKED")
        self.assertTrue(result["do_not_guess_ip"])

    def test_runtime_paths_must_all_be_inside_one_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.assertTrue(
                VALIDATOR.paths_are_isolated(
                    base,
                    base / "state.json",
                    base / "state.lock",
                    base / "state.backup",
                )
            )
            self.assertFalse(
                VALIDATOR.paths_are_isolated(
                    base,
                    base / "state.json",
                    base / "state.lock",
                    ROOT / "data" / "runtime" / "forbidden.backup",
                )
            )

    def test_health_probe_requires_exact_mobile_v2_identity(self) -> None:
        success = VALIDATOR.health_probe(
            "192.168.10.101",
            urlopen_func=lambda *args, **kwargs: FakeResponse(
                {"application_id": "MOBILE_V2"}
            ),
        )
        self.assertEqual(success["status"], 200)
        self.assertEqual(success["application_id"], "MOBILE_V2")
        invalid = VALIDATOR.health_probe(
            "192.168.10.101",
            urlopen_func=lambda *args, **kwargs: FakeResponse(
                {"application_id": "OTHER"}
            ),
        )
        self.assertEqual(invalid["application_id"], "OTHER")
        with self.assertRaisesRegex(ValueError, "loopback or RFC1918"):
            VALIDATOR.health_probe("8.8.8.8")


if __name__ == "__main__":
    unittest.main()
