"""PredixAI Trader market session CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import MarketSessionRecorder  # noqa: E402


def print_session(prefix: str, payload: dict) -> None:
    print(prefix)
    print(f"ID={payload['id']}")
    print(f"ASSET={payload['asset']}")
    print(f"TIMEFRAME={payload['timeframe']}")
    print(f"MODE={payload['mode']}")
    print(f"STATUS={payload['status']}")
    print(f"STARTED_AT={payload['started_at']}")
    print(f"ENDED_AT={payload['ended_at']}")
    print(f"TICKS={payload['tick_count']}")
    print(f"CANDLES={payload['candle_count']}")
    print(f"EVIDENCES={payload['evidence_count']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PredixAI Trader market session recorder.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--asset", required=True)
    start_parser.add_argument("--timeframe", required=True)
    start_parser.add_argument("--mode", default="observer")
    start_parser.add_argument("--notes", default="")
    start_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=10)
    list_parser.add_argument("--json", action="store_true")

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("--id", type=int, required=True)
    get_parser.add_argument("--json", action="store_true")

    close_parser = subparsers.add_parser("close")
    close_parser.add_argument("--id", type=int, required=True)
    close_parser.add_argument("--status", default="completed")
    close_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    recorder = MarketSessionRecorder(args.db_path)

    if args.command == "start":
        session = recorder.start_session(
            asset=args.asset,
            timeframe=args.timeframe,
            mode=args.mode,
            notes=args.notes,
        )
        payload = session.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_session("PREDIXAI_MARKET_SESSION_STARTED", payload)
        return 0

    if args.command == "list":
        sessions = [session.to_dict() for session in recorder.list_sessions(limit=args.limit)]
        if args.json:
            print(json.dumps(sessions, ensure_ascii=False, indent=2))
        else:
            print("PREDIXAI_MARKET_SESSION_LIST")
            print(f"COUNT={len(sessions)}")
            for session in sessions:
                print(f"SESSION={session['id']}|{session['asset']}|{session['timeframe']}|{session['status']}")
        return 0

    if args.command == "get":
        session = recorder.get_session(args.id)
        if session is None:
            print(f"PREDIXAI_MARKET_SESSION_NOT_FOUND={args.id}")
            return 2
        payload = session.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_session("PREDIXAI_MARKET_SESSION_DETAIL", payload)
        return 0

    if args.command == "close":
        session = recorder.close_session(session_id=args.id, status=args.status)
        payload = session.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_session("PREDIXAI_MARKET_SESSION_CLOSED", payload)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
