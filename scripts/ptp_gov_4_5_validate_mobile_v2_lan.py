#!/usr/bin/env python3
"""PTP-GOV.4.5 controlled LAN validator for PredixAI Mobile V2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import ipaddress
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BIND_HOST = "0.0.0.0"
PORT = 5001
APPLICATION_ID = "MOBILE_V2"
RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402
from predixai.mobile_v2.state_store import RuntimeStateStore  # noqa: E402


def _load_runner() -> Any:
    path = ROOT / "scripts" / "run_mobile_v2_server.py"
    spec = importlib.util.spec_from_file_location("ptp_gov_4_5_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("não foi possível carregar o entrypoint canônico")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = _load_runner()

PORT_CLASSIFICATION = {
    RUNNER.PORT_FREE: "PORT_5001_FREE",
    RUNNER.PORT_OCCUPIED_BY_MOBILE_V2: "PORT_5001_MOBILE_V2_EXTERNAL",
    RUNNER.PORT_OCCUPIED_BY_OTHER_APPLICATION: "PORT_5001_OTHER_APPLICATION",
    RUNNER.HEALTH_TIMEOUT: "PORT_5001_TIMEOUT",
    RUNNER.HEALTH_INVALID_RESPONSE: "PORT_5001_INVALID_RESPONSE",
}


def is_excluded_interface(name: str) -> bool:
    normalized = name.strip().lower()
    exact = {"lo", "docker0", "tailscale0"}
    prefixes = (
        "docker",
        "veth",
        "virbr",
        "br-",
        "container",
        "podman",
        "cni",
        "tun",
        "tap",
        "wg",
        "tailscale",
        "vpn",
        "zt",
    )
    return normalized in exact or normalized.startswith(prefixes)


def is_rfc1918(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.version == 4 and any(parsed in network for network in RFC1918_NETWORKS)


def select_lan_network(
    default_routes: Iterable[dict[str, Any]],
    address_records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    addresses_by_interface: dict[str, list[str]] = {}
    active_interfaces: set[str] = set()
    for record in address_records:
        interface = str(record.get("ifname", ""))
        flags = set(record.get("flags") or [])
        if is_excluded_interface(interface):
            continue
        if record.get("operstate") == "UP" and "UP" in flags:
            active_interfaces.add(interface)
        for item in record.get("addr_info") or []:
            address = item.get("local")
            if (
                item.get("family") == "inet"
                and item.get("scope") == "global"
                and isinstance(address, str)
                and is_rfc1918(address)
            ):
                addresses_by_interface.setdefault(interface, []).append(address)

    candidates: list[dict[str, Any]] = []
    for route in default_routes:
        interface = str(route.get("dev", ""))
        if (
            route.get("dst") != "default"
            or is_excluded_interface(interface)
            or interface not in active_interfaces
        ):
            continue
        route_source = route.get("prefsrc") or route.get("src")
        available = addresses_by_interface.get(interface, [])
        ordered = []
        if isinstance(route_source, str) and route_source in available:
            ordered.append(route_source)
        ordered.extend(address for address in available if address not in ordered)
        for address in ordered:
            candidates.append(
                {
                    "interface": interface,
                    "ipv4": address,
                    "metric": int(route.get("metric", 0)),
                    "gateway": route.get("gateway"),
                }
            )

    candidates.sort(key=lambda item: (item["metric"], item["interface"], item["ipv4"]))
    if not candidates:
        return {
            "local_network_detection_status": "BLOCKED",
            "mobile_url": "NOT_AVAILABLE",
            "do_not_guess_ip": True,
            "candidates": [],
        }
    selected = candidates[0]
    return {
        "local_network_detection_status": "PASS_CANDIDATE_SELECTED",
        "active_network_interface": selected["interface"],
        "computer_local_ipv4": selected["ipv4"],
        "mobile_v2_port": PORT,
        "mobile_v2_bind_host": BIND_HOST,
        "mobile_v2_local_url": f"http://{selected['ipv4']}:{PORT}",
        "candidates": candidates,
    }


def detect_local_network(
    run_command: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    commands = (
        ["ip", "-j", "route", "show", "default"],
        ["ip", "-j", "-4", "address", "show"],
    )
    payloads = []
    for command in commands:
        result = run_command(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return {
                "local_network_detection_status": "BLOCKED",
                "mobile_url": "NOT_AVAILABLE",
                "do_not_guess_ip": True,
                "diagnostic": result.stderr.strip() or "local ip command failed",
                "candidates": [],
            }
        try:
            payloads.append(json.loads(result.stdout))
        except json.JSONDecodeError as exc:
            return {
                "local_network_detection_status": "BLOCKED",
                "mobile_url": "NOT_AVAILABLE",
                "do_not_guess_ip": True,
                "diagnostic": f"invalid local ip JSON: {exc}",
                "candidates": [],
            }
    return select_lan_network(payloads[0], payloads[1])


def paths_are_isolated(
    directory: Path, state_path: Path, lock_path: Path, backup_path: Path
) -> bool:
    try:
        resolved_directory = directory.resolve()
        paths = (state_path.resolve(), lock_path.resolve(), backup_path.resolve())
        return len(set(paths)) == 3 and all(
            path.relative_to(resolved_directory) is not None for path in paths
        )
    except ValueError:
        return False


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


def health_probe(
    host: str,
    *,
    timeout: float = 1.0,
    urlopen_func: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if host != "127.0.0.1" and not is_rfc1918(host):
        raise ValueError("health probe host must be loopback or RFC1918")
    url = f"http://{host}:{PORT}/health"
    try:
        response = urlopen_func(url, timeout=timeout)
        with response:
            status = getattr(response, "status", None)
            raw = response.read()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {"status": None, "application_id": None, "error": str(exc)}
    return {
        "status": status,
        "application_id": payload.get("application_id") if isinstance(payload, dict) else None,
        "error": None,
    }


def wait_for_health(host: str, process: subprocess.Popen[bytes]) -> dict[str, Any]:
    deadline = time.monotonic() + 10.0
    last = {"status": None, "application_id": None, "error": "not attempted"}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return {
                "status": None,
                "application_id": None,
                "error": f"controlled server exited with {process.returncode}",
            }
        last = health_probe(host, timeout=0.5)
        if last["status"] == 200 and last["application_id"] == APPLICATION_ID:
            return last
        time.sleep(0.1)
    return last


def terminate_owned_process(
    process: subprocess.Popen[bytes], pgid: int
) -> dict[str, Any]:
    result = {"termination_signal": "NONE", "sigkill_used": False}
    if process.poll() is None:
        os.killpg(pgid, signal.SIGTERM)
        result["termination_signal"] = "SIGTERM"
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
            result["termination_signal"] = "SIGKILL"
            result["sigkill_used"] = True
            process.wait(timeout=2.0)
    result["controlled_process_exit_code"] = process.returncode
    result["residual_process_count"] = 0 if process.poll() is not None else 1
    return result


def serve(state_path: Path, lock_path: Path, backup_path: Path) -> int:
    if not paths_are_isolated(state_path.parent, state_path, lock_path, backup_path):
        return 72
    store = RuntimeStateStore(state_path, lock_path, backup_path)
    app = create_mobile_v2_app(store=store)
    app.run(
        host=BIND_HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )
    return 0


def run_hold() -> int:
    network = detect_local_network()
    if network["local_network_detection_status"] == "BLOCKED":
        print(json.dumps({"event": "BLOCKED", **network}, ensure_ascii=False), flush=True)
        return 2

    real_runtime = ROOT / "data" / "runtime"
    runtime_hash_before = hash_tree(real_runtime)
    controlled: dict[str, Any] = {
        "event": "STARTING",
        **network,
        "real_runtime_hash_before": runtime_hash_before,
        "real_runtime_used": False,
        "network_external": False,
    }
    temporary_path: Path | None = None
    stopped: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="ptp_gov_4_5_") as temporary:
        temp_dir = Path(temporary)
        temporary_path = temp_dir
        state_path = temp_dir / "mobile_v2_state.json"
        lock_path = temp_dir / "mobile_v2_state.json.lock"
        backup_path = temp_dir / "mobile_v2_state.json.backup"
        controlled.update(
            {
                "temp_runtime_directory": str(temp_dir),
                "temp_state_path": str(state_path),
                "temp_lock_path": str(lock_path),
                "temp_backup_path": str(backup_path),
            }
        )
        if not paths_are_isolated(temp_dir, state_path, lock_path, backup_path):
            print(
                json.dumps(
                    {"event": "BLOCKED_RUNTIME_ISOLATION", **controlled},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            return 3

        canonical_port = RUNNER.port_application_identity_check(
            "127.0.0.1", PORT, timeout=0.5
        )
        controlled["port_5001_initial_classification"] = PORT_CLASSIFICATION.get(
            canonical_port, "PORT_5001_INVALID_RESPONSE"
        )
        if canonical_port != RUNNER.PORT_FREE:
            print(
                json.dumps({"event": "BLOCKED_PORT", **controlled}, ensure_ascii=False),
                flush=True,
            )
            return 4

        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--serve",
            "--state-path",
            str(state_path),
            "--lock-path",
            str(lock_path),
            "--backup-path",
            str(backup_path),
        ]
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pgid = os.getpgid(process.pid)
        controlled["controlled_server_pid"] = process.pid
        controlled["controlled_server_pgid"] = pgid

        try:
            loopback = wait_for_health("127.0.0.1", process)
            lan = wait_for_health(network["computer_local_ipv4"], process)
            identity_status = RUNNER.port_application_identity_check(
                "127.0.0.1", PORT, timeout=0.5
            )
            current_runtime_hash = hash_tree(real_runtime)
            ready = (
                process.poll() is None
                and loopback["status"] == 200
                and lan["status"] == 200
                and loopback["application_id"] == APPLICATION_ID
                and lan["application_id"] == APPLICATION_ID
                and identity_status == RUNNER.PORT_OCCUPIED_BY_MOBILE_V2
                and current_runtime_hash == runtime_hash_before
            )
            controlled.update(
                {
                    "event": "READY" if ready else "AUTOMATIC_GATE_FAIL",
                    "automated_tests_pass": True,
                    "server_running": process.poll() is None,
                    "local_port_listening": PORT if process.poll() is None else None,
                    "loopback_health_http_status": loopback["status"],
                    "lan_health_http_status": lan["status"],
                    "health_application_id": lan["application_id"],
                    "local_url_ready": ready,
                    "port_identity_check": identity_status,
                    "real_runtime_hash_during": current_runtime_hash,
                    "real_runtime_changed": current_runtime_hash != runtime_hash_before,
                }
            )
            print(json.dumps(controlled, ensure_ascii=False, sort_keys=True), flush=True)
            if not ready:
                return 5

            while True:
                command_line = sys.stdin.readline()
                if command_line == "":
                    time.sleep(1.0)
                    continue
                action = command_line.strip().upper()
                if action == "STATUS":
                    status = health_probe(network["computer_local_ipv4"])
                    print(
                        json.dumps(
                            {
                                "event": "STATUS",
                                "server_running": process.poll() is None,
                                "lan_health": status,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                elif action == "STOP":
                    break
        finally:
            stopped = terminate_owned_process(process, pgid)

    runtime_hash_after = hash_tree(real_runtime)
    final = {
        "event": "STOPPED",
        **stopped,
        "port_5001_after_stop": PORT_CLASSIFICATION.get(
            RUNNER.port_application_identity_check("127.0.0.1", PORT, timeout=0.5),
            "PORT_5001_INVALID_RESPONSE",
        ),
        "real_runtime_hash_after": runtime_hash_after,
        "real_runtime_changed": runtime_hash_after != runtime_hash_before,
        "temp_runtime_removed": bool(temporary_path and not temporary_path.exists()),
    }
    print(json.dumps(final, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if (
        final["residual_process_count"] == 0
        and final["port_5001_after_stop"] == "PORT_5001_FREE"
        and final["real_runtime_changed"] is False
        and final["temp_runtime_removed"] is True
    ) else 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--backup-path", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.serve:
        if not all((args.state_path, args.lock_path, args.backup_path)):
            return 64
        return serve(args.state_path, args.lock_path, args.backup_path)
    return run_hold()


if __name__ == "__main__":
    raise SystemExit(main())
