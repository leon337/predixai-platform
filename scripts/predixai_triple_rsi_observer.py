"""PredixAI Trader Triple RSI observer CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import TripleRSIObserver  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate Triple RSI snapshots.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    calc_parser = subparsers.add_parser("calculate")
    calc_parser.add_argument("--session-id", type=int, required=True)
    calc_parser.add_argument("--short-period", type=int, default=7)
    calc_parser.add_argument("--medium-period", type=int, default=14)
    calc_parser.add_argument("--long-period", type=int, default=21)
    calc_parser.add_argument("--no-persist", action="store_true")
    calc_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--session-id", type=int, required=True)
    list_parser.add_argument("--limit", type=int, default=10)
    list_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    observer = TripleRSIObserver(args.db_path)

    if args.command == "calculate":
        result = observer.calculate_for_session(
            session_id=args.session_id,
            short_period=args.short_period,
            medium_period=args.medium_period,
            long_period=args.long_period,
            persist=not args.no_persist,
        )
        payload = result.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_TRIPLE_RSI_RESULT")
            print(f"STATUS={payload['status']}")
            print(f"SESSION_ID={payload['session_id']}")
            print(f"TICK_ID={payload['tick_id']}")
            print(f"RSI_SHORT={payload['rsi_short']}")
            print(f"RSI_MEDIUM={payload['rsi_medium']}")
            print(f"RSI_LONG={payload['rsi_long']}")
            print(f"PRICE_COUNT={payload['price_count']}")
            print(f"INDICATOR_SNAPSHOT_ID={payload['indicator_snapshot_id']}")
        return 0

    if args.command == "list":
        snapshots = observer.list_snapshots(session_id=args.session_id, limit=args.limit)
        payload = list(snapshots)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_TRIPLE_RSI_SNAPSHOTS")
            print(f"COUNT={len(payload)}")
            for snapshot in payload:
                print(
                    "SNAPSHOT="
                    f"{snapshot['id']}|{snapshot['session_id']}|{snapshot['tick_id']}|"
                    f"{snapshot['rsi_short']}|{snapshot['rsi_medium']}|{snapshot['rsi_long']}"
                )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
