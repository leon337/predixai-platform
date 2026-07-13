#!/usr/bin/env python3
"""Run PredixAI Mobile V2 as a standalone Flask server.

Default:
  host: 0.0.0.0
  port: 5001

Usage:
  python3 scripts/run_mobile_v2_server.py
  PREDIXAI_MOBILE_V2_PORT=5001 python3 scripts/run_mobile_v2_server.py
"""

from __future__ import annotations

import os
import json
import socket
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402


APPLICATION_ID = "MOBILE_V2"
PORT_FREE = "PORT_FREE"
PORT_OCCUPIED_BY_MOBILE_V2 = "PORT_OCCUPIED_BY_MOBILE_V2"
PORT_OCCUPIED_BY_OTHER_APPLICATION = "PORT_OCCUPIED_BY_OTHER_APPLICATION"
HEALTH_TIMEOUT = "HEALTH_TIMEOUT"
HEALTH_INVALID_RESPONSE = "HEALTH_INVALID_RESPONSE"


def _health_probe_host(host: str) -> str:
    if host in {"0.0.0.0", "::", ""}:
        return "127.0.0.1"
    return host


def port_application_identity_check(
    host: str,
    port: int,
    *,
    timeout: float = 1.0,
    socket_factory: Callable[..., Any] = socket.socket,
    urlopen_func: Callable[..., Any] = urlopen,
) -> str:
    """Classify the configured port without starting or killing any process."""
    probe_host = _health_probe_host(host)
    probe_socket = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe_socket.settimeout(timeout)
        connection_status = probe_socket.connect_ex((probe_host, port))
    finally:
        probe_socket.close()

    if connection_status != 0:
        return PORT_FREE

    try:
        response = urlopen_func(f"http://{probe_host}:{port}/health", timeout=timeout)
        with response:
            status_code = getattr(response, "status", None)
            raw_payload = response.read()
    except (TimeoutError, socket.timeout):
        return HEALTH_TIMEOUT
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return HEALTH_TIMEOUT
        return HEALTH_INVALID_RESPONSE
    except (OSError, ValueError):
        return HEALTH_INVALID_RESPONSE

    if status_code != 200:
        return HEALTH_INVALID_RESPONSE

    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return HEALTH_INVALID_RESPONSE

    if not isinstance(payload, dict):
        return HEALTH_INVALID_RESPONSE

    active_application_id = payload.get("application_id")
    if active_application_id == APPLICATION_ID:
        return PORT_OCCUPIED_BY_MOBILE_V2
    if isinstance(active_application_id, str) and active_application_id.strip():
        return PORT_OCCUPIED_BY_OTHER_APPLICATION
    return HEALTH_INVALID_RESPONSE


def main() -> int:
    host = os.environ.get("PREDIXAI_MOBILE_V2_HOST", "0.0.0.0")
    port = int(os.environ.get("PREDIXAI_MOBILE_V2_PORT", "5001"))
    debug = os.environ.get("PREDIXAI_MOBILE_V2_DEBUG", "0") == "1"

    port_status = port_application_identity_check(host, port)
    if port_status == PORT_OCCUPIED_BY_MOBILE_V2:
        print(
            f"PredixAI Mobile V2 já está ativa em {host}:{port}; "
            "nenhuma instância duplicada foi iniciada."
        )
        return 0
    if port_status != PORT_FREE:
        print(
            f"Inicialização bloqueada: {port_status} em {host}:{port}. "
            "Fallback silencioso de porta é proibido.",
            file=sys.stderr,
        )
        return 2

    app = create_mobile_v2_app()

    print("PredixAI Mobile V2 standalone server")
    print(f"URL local: http://127.0.0.1:{port}")
    print(f"Host: {host}")
    print(f"Porta: {port}")
    print("Legacy mobile_server.py: NÃO usado")
    print("Observer real: NÃO iniciado")
    print("Modo: 100% simulado")

    app.run(host=host, port=port, debug=debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
