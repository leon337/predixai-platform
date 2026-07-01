"""PredixAI Trader data quality score CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from predixai.trader import DataQualityScorer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Score PredixAI Trader evidence quality.")
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    evidence_path = Path(args.evidence_path)
    payload = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    result = DataQualityScorer().score_evidence(payload)
    result_payload = result.to_dict()

    if args.json:
        print(json.dumps(result_payload, ensure_ascii=False, indent=2))
    else:
        print("PREDIXAI_DATA_QUALITY_SCORE")
        print(f"SCORE={result_payload['score']}")
        print(f"LABEL={result_payload['label']}")
        print(f"USABLE_FOR_MEMORY={result_payload['usable_for_memory']}")
        print(f"WARNINGS={','.join(result_payload['warnings']) if result_payload['warnings'] else 'none'}")

    return 0 if result.score >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
