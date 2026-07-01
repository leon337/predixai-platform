"""PredixAI Trader DB status script."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import TraderDataStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="PredixAI Trader SQLite status.")
    parser.add_argument("--init", action="store_true", help="Initialize database before status.")
    parser.add_argument(
        "--db-path",
        default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"),
        help="SQLite database path.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON status.")
    args = parser.parse_args()

    store = TraderDataStore(args.db_path)
    status = store.initialize() if args.init else store.status()
    payload = status.to_dict()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("PREDIXAI_TRADER_DB_STATUS")
        print(f"OK={payload['ok']}")
        print(f"DB_PATH={payload['db_path']}")
        print(f"EXISTS={payload['exists']}")
        print(f"SCHEMA_VERSION={payload['schema_version']}")
        print(f"TABLES={','.join(payload['tables']) if payload['tables'] else 'none'}")

    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
