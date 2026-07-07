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
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402


def main() -> int:
    host = os.environ.get("PREDIXAI_MOBILE_V2_HOST", "0.0.0.0")
    port = int(os.environ.get("PREDIXAI_MOBILE_V2_PORT", "5001"))
    debug = os.environ.get("PREDIXAI_MOBILE_V2_DEBUG", "0") == "1"

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
