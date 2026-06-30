"""PredixAI supervised task protocol.

Classifies local tasks before handoff to OpenClaw/Ollama.
Does not trade, click, open broker automation, place orders, or require paid APIs.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "tools" / "openclaw" / "reports"

BLOCK_PATTERNS = {
    "broker_automation": [
        r"\bcorretora\b",
        r"\bbroker\b",
        r"\bapi\s+da\s+corretora\b",
        r"\bautomatizar\s+corretora\b",
    ],
    "real_account": [
        r"\bconta\s+real\b",
        r"\bdinheiro\s+real\b",
        r"\bbanca\s+real\b",
    ],
    "orders_or_clicks": [
        r"\bexecutar\s+ordem\b",
        r"\bordem\s+real\b",
        r"\bclicar\b",
        r"\bcomprar\b",
        r"\bvender\b",
        r"\bentrada\s+automatica\b",
        r"\boperação\s+automatica\b",
        r"\boperacao\s+automatica\b",
    ],
    "profit_promise": [
        r"\blucro\s+garantido\b",
        r"\bpromessa\s+de\s+lucro\b",
        r"\bgarantir\s+lucro\b",
    ],
    "paid_api_required": [
        r"\bapi\s+paga\s+obrigatoria\b",
        r"\bapi\s+paga\s+obrigatória\b",
    ],
}

APPROVAL_PATTERNS = {
    "git_publication": [
        r"\bcommit\b",
        r"\bpush\b",
        r"\bpublicar\b",
        r"\bgithub\b",
    ],
    "documentation_update": [
        r"\bproject_state\.md\b",
        r"\bchangelog\.md\b",
        r"\bpredixai_context\.json\b",
    ],
    "agent_execution": [
        r"\bopenclaw\b",
        r"\bollama\b",
        r"\bagente\b",
        r"\bhandoff\b",
    ],
    "file_modification": [
        r"\bcriar\b",
        r"\balterar\b",
        r"\bremover\b",
        r"\bdeletar\b",
        r"\beditar\b",
    ],
}

SAFE_HINTS = [
    "diagnostico",
    "diagnóstico",
    "status",
    "validar",
    "testar",
    "compileall",
    "json",
    "diff check",
    "relatorio",
    "relatório",
]


def normalize(text: str) -> str:
    return text.strip().lower()


def find_matches(text: str, patterns: dict[str, list[str]]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for category, items in patterns.items():
        hits = []
        for pattern in items:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(pattern)
        if hits:
            found[category] = hits
    return found


def classify_task(task: str) -> dict[str, object]:
    text = normalize(task)

    blocked_matches = find_matches(text, BLOCK_PATTERNS)
    approval_matches = find_matches(text, APPROVAL_PATTERNS)
    safe_hits = [hint for hint in SAFE_HINTS if hint in text]

    if blocked_matches:
        classification = "BLOCKED"
        allowed_actions = [
            "generate_safe_report",
            "explain_scope_limit",
            "request_architect_review",
        ]
        required_approval = True
        can_call_agent = False
    elif approval_matches:
        classification = "NEEDS_APPROVAL"
        allowed_actions = [
            "generate_plan",
            "generate_diff",
            "run_minimal_validation",
            "wait_for_leo_approval",
        ]
        required_approval = True
        can_call_agent = False
    else:
        classification = "SAFE_LOCAL"
        allowed_actions = [
            "generate_report",
            "run_fast_status",
            "run_compileall",
            "run_json_validation",
            "run_diff_check",
        ]
        required_approval = False
        can_call_agent = False

    return {
        "classification": classification,
        "required_approval": required_approval,
        "can_call_agent": can_call_agent,
        "allowed_actions": allowed_actions,
        "blocked_matches": blocked_matches,
        "approval_matches": approval_matches,
        "safe_hints": safe_hits,
    }


def build_envelope(task: str, source: str) -> dict[str, object]:
    protocol = classify_task(task)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "protocol": "PredixAI Supervised Task Protocol",
        "ptp": "PTP-094",
        "source": source,
        "task": task,
        "result": protocol,
        "scope": {
            "product": "PredixAI Trader",
            "mode": "V1 Observador",
            "broker_clicks_enabled": False,
            "orders_enabled": False,
            "broker_automation_enabled": False,
            "real_account_enabled": False,
            "profit_promise_allowed": False,
            "paid_api_required": False,
        },
    }


def print_summary(envelope: dict[str, object]) -> None:
    result = envelope["result"]
    print("PREDIXAI_TASK_PROTOCOL")
    print(f"CLASSIFICATION={result['classification']}")
    print(f"REQUIRED_APPROVAL={result['required_approval']}")
    print(f"CAN_CALL_AGENT={result['can_call_agent']}")
    print(f"ALLOWED_ACTIONS={','.join(result['allowed_actions'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PredixAI supervised task protocol.")
    parser.add_argument("--task", required=True, help="Task to classify.")
    parser.add_argument("--source", default="leo", help="Task source.")
    parser.add_argument("--json", action="store_true", help="Print full JSON envelope.")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    envelope = build_envelope(task=args.task, source=args.source)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    report_path = REPORTS_DIR / f"predixai_task_protocol_{stamp}.json"
    report_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        print_summary(envelope)

    print(f"PREDIXAI_TASK_PROTOCOL_REPORT={report_path}")

    return 0 if envelope["result"]["classification"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())

