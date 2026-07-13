#!/usr/bin/env python3
"""PTP-GOV.4.3: controlled local runtime validation for Mobile V2.

The validator starts only its own localhost process and injects every runtime
path into one TemporaryDirectory. It never selects another port, kills an
external process, contacts an external host, or accesses the real runtime for
application state. The real runtime is hashed read-only before and after.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
HOST = "127.0.0.1"
PORT = 5001
APPLICATION_ID = "MOBILE_V2"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402
from predixai.mobile_v2.state_store import (  # noqa: E402
    RuntimeStateBackupError,
    RuntimeStateStore,
)


def _load_entrypoint_module() -> Any:
    path = ROOT / "scripts" / "run_mobile_v2_server.py"
    spec = importlib.util.spec_from_file_location("ptp_gov_4_3_entrypoint", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("não foi possível carregar o entrypoint canônico")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENTRYPOINT = _load_entrypoint_module()

PORT_CLASSIFICATION = {
    ENTRYPOINT.PORT_FREE: "PORT_5001_FREE",
    ENTRYPOINT.PORT_OCCUPIED_BY_MOBILE_V2: "PORT_5001_MOBILE_V2_EXTERNAL",
    ENTRYPOINT.PORT_OCCUPIED_BY_OTHER_APPLICATION: "PORT_5001_OTHER_APPLICATION",
    ENTRYPOINT.HEALTH_INVALID_RESPONSE: "PORT_5001_INVALID_RESPONSE",
    ENTRYPOINT.HEALTH_TIMEOUT: "PORT_5001_TIMEOUT",
}


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _validate_runtime_paths(
    directory: Path, state_path: Path, lock_path: Path, backup_path: Path
) -> bool:
    paths = (state_path, lock_path, backup_path)
    return len({path.resolve() for path in paths}) == 3 and all(
        _is_within(path, directory) for path in paths
    )


def _hash_tree(path: Path) -> str:
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


def _local_request(
    method: str,
    route: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 1.0,
) -> tuple[int, bytes, str]:
    url = f"http://{HOST}:{PORT}{route}"
    parsed = urlparse(url)
    if parsed.hostname != "127.0.0.1" or parsed.port != 5001:
        raise ValueError("somente 127.0.0.1:5001 é permitido")
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get_content_type()
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get_content_type()


def _json_body(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("resposta JSON não é objeto")
    return payload


def _classify_port() -> tuple[str, str]:
    canonical = ENTRYPOINT.port_application_identity_check(HOST, PORT, timeout=0.5)
    return canonical, PORT_CLASSIFICATION.get(canonical, "PORT_5001_INVALID_RESPONSE")


def _serve(state_path: Path, lock_path: Path, backup_path: Path) -> int:
    directory = state_path.parent
    if not _validate_runtime_paths(directory, state_path, lock_path, backup_path):
        return 72
    store = RuntimeStateStore(
        state_path=state_path,
        lock_path=lock_path,
        backup_path=backup_path,
    )
    app = create_mobile_v2_app(store)
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
    return 0


def _terminate_owned_process(process: subprocess.Popen[bytes], pgid: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "termination_signal": "NONE",
        "sigkill_used": False,
        "controlled_process_exit_code": None,
        "residual_process_count": 0,
    }
    if process.poll() is None:
        os.killpg(pgid, signal.SIGTERM)
        result["termination_signal"] = "SIGTERM"
        try:
            process.wait(timeout=4.0)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
            result["termination_signal"] = "SIGKILL"
            result["sigkill_used"] = True
            process.wait(timeout=2.0)
    result["controlled_process_exit_code"] = process.returncode
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        result["residual_process_count"] = 0
    except PermissionError:
        result["residual_process_count"] = 1
    else:
        result["residual_process_count"] = 1
    return result


def run_validation() -> tuple[int, dict[str, Any]]:
    real_runtime = ROOT / "data" / "runtime"
    real_state = RuntimeStateStore().state_path
    real_runtime_hash_before = _hash_tree(real_runtime)
    result: dict[str, Any] = {
        "ptp": "PTP-GOV.4.3",
        "execution_status": "FAIL_RUNTIME_VALIDATION",
        "runtime_path_injection_available": True,
        "real_state_path": str(real_state),
        "real_runtime_hash_before": real_runtime_hash_before,
        "real_runtime_hash_after": None,
        "real_runtime_changed": None,
        "temp_state_path": None,
        "temp_lock_path": None,
        "temp_backup_path": None,
        "port_5001_classification": None,
        "controlled_server_pid": None,
        "controlled_server_pgid": None,
        "health_application_id": None,
        "controlled_runtime_http": "FAIL",
        "port_identity_check": "FAIL",
        "backup_recovery_temp_runtime": "FAIL",
        "backup_created": "FAIL",
        "backup_schema_valid": "FAIL",
        "recovery_explicit": "FAIL",
        "recovered_state_match": "FAIL",
        "invalid_backup_controlled_error": "FAIL",
        "bind_host": HOST,
        "port": PORT,
        "external_network_used": False,
        "real_runtime_used": False,
        "temp_runtime_directory": True,
        "project_server_started": False,
        "legacy_started": False,
        "dashboard_started": False,
        "broker_opened": False,
        "real_money_enabled": False,
        "real_order_enabled": False,
        "auto_click_enabled": False,
        "broker_login_automation": False,
        "http_results": [],
        "errors": [],
    }
    process: subprocess.Popen[bytes] | None = None
    pgid: int | None = None

    with tempfile.TemporaryDirectory(prefix="ptp_gov_4_3_") as temporary:
        temp_dir = Path(temporary)
        state_path = temp_dir / "mobile_v2_state.json"
        lock_path = temp_dir / "mobile_v2_state.json.lock"
        backup_path = temp_dir / "mobile_v2_state.json.backup"
        result.update(
            {
                "temp_runtime_directory_path": str(temp_dir),
                "temp_state_path": str(state_path),
                "temp_lock_path": str(lock_path),
                "temp_backup_path": str(backup_path),
            }
        )

        if not _validate_runtime_paths(temp_dir, state_path, lock_path, backup_path):
            result["runtime_path_injection_available"] = False
            result["execution_status"] = "BLOCKED_RUNTIME_ISOLATION"
            result["project_server_started"] = False
            result["real_runtime_hash_after"] = _hash_tree(real_runtime)
            result["real_runtime_changed"] = (
                result["real_runtime_hash_after"] != real_runtime_hash_before
            )
            return 2, result

        try:
            _, port_classification = _classify_port()
            result["port_5001_classification"] = port_classification
            if port_classification != "PORT_5001_FREE":
                result["execution_status"] = "BLOCKED_PORT_5001"
                result["project_server_started"] = False
                return 3, result

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
            result["project_server_started"] = True
            pgid = os.getpgid(process.pid)
            result["controlled_server_pid"] = process.pid
            result["controlled_server_pgid"] = pgid

            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"servidor controlado encerrou com código {process.returncode}"
                    )
                try:
                    status, raw, _ = _local_request("GET", "/health", timeout=0.4)
                    health = _json_body(raw)
                    if status == 200 and health.get("application_id") == APPLICATION_ID:
                        result["health_application_id"] = health["application_id"]
                        break
                except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("timeout de prontidão do /health")

            canonical_port_status, _ = _classify_port()
            if canonical_port_status != ENTRYPOINT.PORT_OCCUPIED_BY_MOBILE_V2:
                raise RuntimeError(
                    f"identidade na porta não reconhecida: {canonical_port_status}"
                )
            result["port_identity_check"] = "PASS"

            routes = [
                ("GET", "/", None),
                ("GET", "/health", None),
                ("GET", "/session/setup", None),
                (
                    "POST",
                    "/session/create",
                    {
                        "initial_bank": 100.0,
                        "entry_value": 5.0,
                        "profit_goal": 10.0,
                        "recovery_mode": "sem_recuperacao",
                        "asset_label": "SIMULADO",
                    },
                ),
                ("GET", "/mobile", None),
                ("GET", "/state/current", None),
                ("POST", "/observer/start", {}),
                ("POST", "/observer/stop", {}),
            ]
            for method, route, payload in routes:
                status, raw, content_type = _local_request(method, route, payload)
                row: dict[str, Any] = {
                    "method": method,
                    "route": route,
                    "http_status": status,
                    "content_type": content_type,
                    "result": "PASS" if status == 200 else "FAIL",
                }
                if content_type == "application/json":
                    body = _json_body(raw)
                    row["ok"] = body.get("ok")
                    if route == "/health":
                        row["application_id"] = body.get("application_id")
                    state = body.get("state")
                    if isinstance(state, dict):
                        session = state.get("session", {})
                        if isinstance(session, dict):
                            row["simulation_only"] = session.get("simulation_only")
                            row["orders_enabled"] = session.get("orders_enabled")
                            row["real_money_enabled"] = session.get("real_money_enabled")
                            row["auto_click_enabled"] = session.get("auto_click_enabled")
                result["http_results"].append(row)
                if status != 200:
                    raise RuntimeError(f"{method} {route} retornou HTTP {status}")

            unsafe = [
                row
                for row in result["http_results"]
                if row.get("simulation_only") is False
                or row.get("orders_enabled") is True
                or row.get("real_money_enabled") is True
                or row.get("auto_click_enabled") is True
            ]
            if unsafe:
                raise RuntimeError("payload HTTP violou os bloqueios de segurança")
            result["controlled_runtime_http"] = "PASS"

            store = RuntimeStateStore(state_path, lock_path, backup_path)
            backup_state = store.create_backup()
            result["backup_created"] = "PASS" if backup_path.is_file() else "FAIL"
            result["backup_schema_valid"] = (
                "PASS"
                if backup_state.get("schema_version") == "mobile_v2_state_v1"
                else "FAIL"
            )
            changed = copy.deepcopy(store.read_state())
            changed["status"] = "ptp_gov_4_3_recovery_probe"
            store.write_state(changed)
            recovered = store.recover_from_backup()
            result["recovery_explicit"] = "PASS"
            result["recovered_state_match"] = (
                "PASS" if recovered == backup_state and store.read_state() == backup_state else "FAIL"
            )

            valid_state_before_invalid_probe = store.read_state()
            backup_path.write_text(
                '{"schema_version":"invalid_backup"}\n', encoding="utf-8"
            )
            try:
                store.recover_from_backup()
            except RuntimeStateBackupError:
                result["invalid_backup_controlled_error"] = (
                    "PASS"
                    if store.read_state() == valid_state_before_invalid_probe
                    else "FAIL"
                )
            else:
                result["invalid_backup_controlled_error"] = "FAIL"

            backup_checks = (
                "backup_created",
                "backup_schema_valid",
                "recovery_explicit",
                "recovered_state_match",
                "invalid_backup_controlled_error",
            )
            if all(result[name] == "PASS" for name in backup_checks):
                result["backup_recovery_temp_runtime"] = "PASS"
            else:
                raise RuntimeError("validação de backup/recovery não passou")

        except Exception as exc:  # controlled evidence capture
            result["errors"].append(f"{type(exc).__name__}: {exc}")
        finally:
            if process is not None and pgid is not None:
                result.update(_terminate_owned_process(process, pgid))
            try:
                _, after_stop_classification = _classify_port()
                result["port_5001_after_stop"] = after_stop_classification
            except Exception as exc:
                result["port_5001_after_stop"] = f"ERROR: {type(exc).__name__}: {exc}"

            real_runtime_hash_after = _hash_tree(real_runtime)
            result["real_runtime_hash_after"] = real_runtime_hash_after
            result["real_runtime_changed"] = (
                real_runtime_hash_after != real_runtime_hash_before
            )

    acceptance = (
        result["health_application_id"] == APPLICATION_ID
        and result["controlled_runtime_http"] == "PASS"
        and result["port_identity_check"] == "PASS"
        and result["backup_recovery_temp_runtime"] == "PASS"
        and result["real_runtime_changed"] is False
        and result.get("residual_process_count") == 0
        and result.get("port_5001_after_stop") == "PORT_5001_FREE"
        and not result["errors"]
    )
    result["runtime_validation_fail"] = not acceptance
    result["functional_fix_applied"] = False
    result["next_ptp_required"] = not acceptance
    result["execution_status"] = (
        "PASS_CONTROLLED_RUNTIME_VALIDATION"
        if acceptance
        else "FAIL_RUNTIME_VALIDATION"
    )
    return (0 if acceptance else 1), result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--backup-path", type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.serve:
        if not all((args.state_path, args.lock_path, args.backup_path)):
            return 64
        return _serve(args.state_path, args.lock_path, args.backup_path)
    code, result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
