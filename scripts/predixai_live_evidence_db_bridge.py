"""PredixAI Trader live evidence DB bridge CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import LiveEvidenceDBBridge  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest live evidence JSON into Trader DB.")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "data" / "predixai_trader.sqlite3"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--evidence-path", required=True)
    ingest_parser.add_argument("--session-id", type=int)
    ingest_parser.add_argument("--asset", default="UNKNOWN")
    ingest_parser.add_argument("--timeframe", default="M1")
    ingest_parser.add_argument("--json", action="store_true")

    latest_parser = subparsers.add_parser("ingest-latest")
    latest_parser.add_argument("--evidence-dir", default=str(REPO_ROOT / "data" / "live_evidence"))
    latest_parser.add_argument("--session-id", type=int)
    latest_parser.add_argument("--asset", default="UNKNOWN")
    latest_parser.add_argument("--timeframe", default="M1")
    latest_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    bridge = LiveEvidenceDBBridge(args.db_path)

    if args.command == "ingest":
        result = bridge.ingest_evidence_file(
            evidence_path=args.evidence_path,
            session_id=args.session_id,
            asset=args.asset,
            timeframe=args.timeframe,
        )
    elif args.command == "ingest-latest":
        result = bridge.ingest_latest_evidence(
            evidence_dir=args.evidence_dir,
            session_id=args.session_id,
            asset=args.asset,
            timeframe=args.timeframe,
        )
    else:
        return 1

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("PREDIXAI_LIVE_EVIDENCE_DB_INGESTED")
        print(f"STATUS={payload['status']}")
        print(f"SESSION_ID={payload['session_id']}")
        print(f"TICK_ID={payload['tick_id']}")
        print(f"EVIDENCE_RECORD_ID={payload['evidence_record_id']}")
        print(f"ASSET={payload['asset']}")
        print(f"TIMEFRAME={payload['timeframe']}")
        print(f"PRICE={payload['price']}")
        print(f"QUALITY_SCORE={payload['quality_score']}")
        print(f"EVIDENCE_PATH={payload['evidence_path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
