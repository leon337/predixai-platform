"""PredixAI supervised runtime status.

Fast local checker for the PredixAI BR runtime.
Does not trade, click, open broker automation, or require paid APIs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "tools" / "openclaw" / "reports"

REQUIRED_FILES = [
    "PROJECT_STATE.md",
    "predixai_context.json",
    "scripts/predixai_agent.bat",
    "scripts/predixai_agent_runner.py",
    "scripts/predixai_handoff.bat",
    "scripts/predixai_handoff_runner.py",
]

REQUIRED_MODEL = "qwen2.5:1.5b"


def run_command(command: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        return completed.returncode, output
    except FileNotFoundError:
        return 127, f"COMMAND_NOT_FOUND: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"COMMAND_TIMEOUT: {' '.join(command)}"


def check_file(path_text: str) -> dict[str, object]:
    path = REPO_ROOT / path_text
    return {
        "name": path_text,
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
    }


def load_context() -> tuple[bool, dict | None, str | None]:
    path = REPO_ROOT / "predixai_context.json"
    try:
        return True, json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return False, None, str(exc)


def build_report(agent_test: bool) -> dict[str, object]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    json_ok, context, json_error = load_context()

    git_status_code, git_status = run_command(["git", "status", "-sb"])
    git_head_code, git_head = run_command(["git", "log", "-1", "--oneline"])

    python_code, python_version = run_command(["python", "--version"])
    node_code, node_version = run_command(["node", "--version"])
    npm_code, npm_version = run_command(["npm", "--version"])
    ollama_code, ollama_version = run_command(["ollama", "--version"])
    ollama_list_code, ollama_list = run_command(["ollama", "list"])
    openclaw_path_code, openclaw_path = run_command(["where.exe", "openclaw"])
    openclaw_models_code, openclaw_models_status = run_command(
        ["openclaw", "models", "status"],
        timeout=60,
    )

    model_found = REQUIRED_MODEL.lower() in ollama_list.lower()

    files = [check_file(item) for item in REQUIRED_FILES]
    missing_files = [item["name"] for item in files if not item["exists"]]

    scope_guardrails = {}
    if context:
        scope_guardrails = context.get("scope_guardrails", {}) or {}

    required_false_guardrails = [
        "broker_clicks_enabled",
        "orders_enabled",
        "broker_automation_enabled",
        "decision_making_enabled",
        "profit_promise_allowed",
    ]

    guardrail_failures = [
        key for key in required_false_guardrails
        if scope_guardrails.get(key) is not False
    ]
    hard_blocks_ok = not guardrail_failures

    agent_test_result = "SKIPPED"
    agent_test_output = ""

    if agent_test:
        agent_code, agent_output = run_command(
            [
                "cmd",
                "/c",
                "scripts\\predixai_handoff.bat",
                "--task",
                "Responda em uma linha: runtime PredixAI supervisionado ativo.",
                "--timeout",
                "240",
            ],
            timeout=300,
        )
        agent_test_output = agent_output
        agent_test_result = (
            "OK"
            if agent_code == 0 and "PREDIXAI_HANDOFF_OK" in agent_output
            else "ERROR"
        )

    critical_checks = {
        "git_status": git_status_code == 0,
        "git_head": git_head_code == 0,
        "python": python_code == 0,
        "node": node_code == 0,
        "ollama_version": ollama_code == 0,
        "ollama_list": ollama_list_code == 0,
        "openclaw_path": openclaw_path_code == 0,
        "json": json_ok,
        "model_found": model_found,
        "required_files": not missing_files,
        "guardrails": hard_blocks_ok,
        "agent_test": agent_test_result in ("SKIPPED", "OK"),
    }

    warning_checks = {
        "npm": npm_code == 0,
        "openclaw_models_status": openclaw_models_code == 0,
    }

    failed_checks = [name for name, ok in critical_checks.items() if not ok]
    warnings = [name for name, ok in warning_checks.items() if not ok]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runtime": "PredixAI Supervised Runtime",
        "ptp": "PTP-093",
        "ok": not failed_checks,
        "critical_checks": critical_checks,
        "warning_checks": warning_checks,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "agent_test": agent_test_result,
        "git": {
            "status_code": git_status_code,
            "head_code": git_head_code,
            "status": git_status,
            "head": git_head,
        },
        "tools": {
            "python_code": python_code,
            "python": python_version,
            "node_code": node_code,
            "node": node_version,
            "npm_code": npm_code,
            "npm": npm_version,
            "ollama_code": ollama_code,
            "ollama": ollama_version,
            "openclaw_path_code": openclaw_path_code,
            "openclaw_path": openclaw_path,
            "openclaw_models_status_code": openclaw_models_code,
            "openclaw_models_status": openclaw_models_status[-4000:] if openclaw_models_status else "",
        },
        "local_model": {
            "required": REQUIRED_MODEL,
            "found": model_found,
            "ollama_list": ollama_list,
        },
        "context": {
            "json_ok": json_ok,
            "json_error": json_error,
            "last_approved_ptp": context.get("last_approved_ptp") if context else None,
            "next_pending_ptp": context.get("next_pending_ptp") if context else None,
            "openclaw_status": (context.get("openclaw") or {}).get("status") if context else None,
        },
        "guardrails": {
            "hard_blocks_ok": hard_blocks_ok,
            "failures": guardrail_failures,
            "scope_guardrails": scope_guardrails,
        },
        "files": {
            "missing": missing_files,
            "checked": files,
        },
        "agent_output": agent_test_output[-4000:] if agent_test_output else "",
    }


def print_summary(report: dict[str, object]) -> None:
    git = report["git"]
    context = report["context"]
    local_model = report["local_model"]
    guardrails = report["guardrails"]
    files = report["files"]

    print("PREDIXAI_RUNTIME_STATUS")
    print(f"OK={report['ok']}")
    print(f"PTP={report['ptp']}")
    print(f"AGENT_TEST={report['agent_test']}")
    print(f"GIT_HEAD={git['head']}")
    print(f"JSON_OK={context['json_ok']}")
    print(f"MODEL_FOUND={local_model['found']}")
    print(f"GUARDRAILS_OK={guardrails['hard_blocks_ok']}")
    print(f"MISSING_FILES={','.join(files['missing']) if files['missing'] else 'none'}")
    print(f"FAILED_CHECKS={','.join(report['failed_checks']) if report['failed_checks'] else 'none'}")
    print(f"WARNINGS={','.join(report['warnings']) if report['warnings'] else 'none'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PredixAI supervised runtime status.")
    parser.add_argument("--agent-test", action="store_true", help="Run one slow supervised agent call.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    report = build_report(agent_test=args.agent_test)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"predixai_runtime_status_{stamp}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_summary(report)

    print(f"PREDIXAI_RUNTIME_REPORT={report_path}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
