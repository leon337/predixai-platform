"""PredixAI Trader support/resistance zone CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import SupportResistanceZoneDetector  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect support/resistance zones.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--session-id", type=int, required=True)
    detect_parser.add_argument("--tolerance-percent", type=float, default=0.25)
    detect_parser.add_argument("--min-touches", type=int, default=2)
    detect_parser.add_argument("--no-persist", action="store_true")
    detect_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--session-id", type=int, required=True)
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    detector = SupportResistanceZoneDetector(args.db_path)

    if args.command == "detect":
        zones = detector.detect_for_session(
            session_id=args.session_id,
            tolerance_percent=args.tolerance_percent,
            min_touches=args.min_touches,
            persist=not args.no_persist,
        )
        payload = [zone.to_dict() for zone in zones]
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_SUPPORT_RESISTANCE_ZONES")
            print(f"COUNT={len(payload)}")
            for zone in payload:
                print(
                    "ZONE="
                    f"{zone['zone_id']}|{zone['zone_type']}|"
                    f"{zone['lower_price']}|{zone['upper_price']}|"
                    f"{zone['mid_price']}|touches={zone['touch_count']}|"
                    f"strength={zone['strength_score']}"
                )
        return 0

    if args.command == "list":
        zones = detector.list_zones(session_id=args.session_id, limit=args.limit)
        payload = list(zones)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_SUPPORT_RESISTANCE_ZONE_LIST")
            print(f"COUNT={len(payload)}")
            for zone in payload:
                print(
                    "ZONE="
                    f"{zone['id']}|{zone['zone_type']}|"
                    f"{zone['lower_price']}|{zone['upper_price']}|"
                    f"{zone['mid_price']}|touches={zone['touch_count']}|"
                    f"strength={zone['strength_score']}"
                )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
