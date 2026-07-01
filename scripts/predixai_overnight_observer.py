"""PredixAI Trader Overnight Observer CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import OvernightObserver  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervised overnight observer sessions.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--asset", required=True)
    run_parser.add_argument("--timeframe", default="M1")
    run_parser.add_argument("--cycles", type=int, default=30)
    run_parser.add_argument("--sleep-seconds", type=float, default=0.0)
    run_parser.add_argument("--synthetic", action="store_true")
    run_parser.add_argument("--close-session", action="store_true")
    run_parser.add_argument(
        "--report-dir",
        default=str(REPO_ROOT / "data" / "runtime" / "overnight_observer"),
    )
    run_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    observer = OvernightObserver(args.db_path)

    if args.command == "run":
        result = observer.run(
            asset=args.asset,
            timeframe=args.timeframe,
            cycles=args.cycles,
            sleep_seconds=args.sleep_seconds,
            synthetic=args.synthetic,
            close_session=args.close_session,
            report_dir=args.report_dir,
        )
        payload = result.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_OVERNIGHT_OBSERVER_COMPLETED")
            print(f"STATUS={payload['status']}")
            print(f"SESSION_ID={payload['session_id']}")
            print(f"ASSET={payload['asset']}")
            print(f"TIMEFRAME={payload['timeframe']}")
            print(f"CYCLE_COUNT={payload['cycle_count']}")
            print(f"REPORT_PATH={payload['report_path']}")
            latest = payload.get("latest_cycle") or {}
            print(f"LATEST_REBOUND_STATUS={latest.get('rebound_status')}")
            print(f"LATEST_REBOUND_LABEL={latest.get('rebound_label')}")
            print(f"LATEST_CONFIDENCE_SCORE={latest.get('confidence_score')}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
