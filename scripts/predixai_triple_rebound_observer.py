"""PredixAI Trader Triple Rebound observer CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import TripleReboundObserver  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe Triple Rebound context.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument("--session-id", type=int, required=True)
    observe_parser.add_argument("--max-zone-distance-percent", type=float, default=0.35)
    observe_parser.add_argument("--min-zone-strength", type=float, default=50.0)
    observe_parser.add_argument("--no-persist", action="store_true")
    observe_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--session-id", type=int, required=True)
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    observer = TripleReboundObserver(args.db_path)

    if args.command == "observe":
        result = observer.observe_for_session(
            session_id=args.session_id,
            max_zone_distance_percent=args.max_zone_distance_percent,
            min_zone_strength=args.min_zone_strength,
            persist=not args.no_persist,
        )
        payload = result.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_TRIPLE_REBOUND_OBSERVATION")
            print(f"STATUS={payload['status']}")
            print(f"OBSERVATION_ID={payload['observation_id']}")
            print(f"SESSION_ID={payload['session_id']}")
            print(f"TICK_ID={payload['tick_id']}")
            print(f"ZONE_ID={payload['zone_id']}")
            print(f"ZONE_TYPE={payload['zone_type']}")
            print(f"LATEST_PRICE={payload['latest_price']}")
            print(f"DISTANCE_TO_ZONE_PERCENT={payload['distance_to_zone_percent']}")
            print(f"RSI_SHORT={payload['rsi_short']}")
            print(f"RSI_MEDIUM={payload['rsi_medium']}")
            print(f"RSI_LONG={payload['rsi_long']}")
            print(f"CONFIDENCE_SCORE={payload['confidence_score']}")
            print(f"OBSERVATION_LABEL={payload['observation_label']}")
        return 0

    if args.command == "list":
        observations = observer.list_observations(session_id=args.session_id, limit=args.limit)
        payload = list(observations)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_TRIPLE_REBOUND_OBSERVATION_LIST")
            print(f"COUNT={len(payload)}")
            for observation in payload:
                print(
                    "OBSERVATION="
                    f"{observation['id']}|{observation['session_id']}|"
                    f"{observation['zone_type']}|{observation['observation_label']}|"
                    f"confidence={observation['confidence_score']}"
                )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
