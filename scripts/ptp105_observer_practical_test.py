from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
RUNTIME_DIR = REPO_ROOT / "data" / "runtime" / "ptp105_observer_practical_test"
STEPS_DIR = RUNTIME_DIR / "steps"

REPORT_JSON = RUNTIME_DIR / "PTP105_OBSERVER_PRACTICAL_TEST_REPORT.json"
REPORT_TXT = RUNTIME_DIR / "PTP105_OBSERVER_PRACTICAL_TEST_REPORT.txt"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_agent(agent_name: str, command: list[str], expects_json: bool = False) -> dict:
    print(f"\n[PTP-105] Iniciando agente: {agent_name}")

    started_at = now_iso()

    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )

    ended_at = now_iso()

    STEPS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = agent_name.lower().replace(" ", "_").replace("-", "_")

    stdout_path = STEPS_DIR / f"{safe_name}_stdout.txt"
    stderr_path = STEPS_DIR / f"{safe_name}_stderr.txt"

    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")

    parsed_json = None
    parse_error = None

    if expects_json and result.stdout.strip():
        try:
            parsed_json = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            parse_error = str(error)

    status = "PASS" if result.returncode == 0 and parse_error is None else "FAIL"

    print(f"[PTP-105] Agente finalizado: {agent_name} | STATUS={status}")

    return {
        "agent_name": agent_name,
        "status": status,
        "returncode": result.returncode,
        "command": command,
        "started_at": started_at,
        "ended_at": ended_at,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "json": parsed_json,
        "parse_error": parse_error,
    }


def write_txt_report(report: dict) -> None:
    lines = [
        "PTP-105 — TRADER V1 OBSERVER PRACTICAL TEST",
        "",
        f"STATUS: {report['status']}",
        f"STARTED_AT: {report['started_at']}",
        f"ENDED_AT: {report['ended_at']}",
        f"SESSION_ID: {report.get('session_id')}",
        "",
        "SAFETY:",
        "- Modo Observador",
        "- Sem trade real",
        "- Sem clique",
        "- Sem ordem",
        "- Sem dinheiro real",
        "",
        "AGENTES EXECUTADOS:",
    ]

    for agent in report["agents"]:
        lines.append(f"- {agent['agent_name']}: {agent['status']}")

    lines.extend(
        [
            "",
            "ARQUIVOS GERADOS:",
            f"- JSON: {REPORT_JSON}",
            f"- TXT: {REPORT_TXT}",
            f"- Evidências: {STEPS_DIR}",
        ]
    )

    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="PTP-105 Observer Practical Test Runner")
    parser.add_argument("--asset", default="TEST_SYNTHETIC")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--cycles", type=int, default=30)

    args = parser.parse_args()

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "ptp": "PTP-105",
        "title": "TRADER V1 OBSERVER PRACTICAL TEST",
        "mode": "observer",
        "real_trade": False,
        "clicks": False,
        "orders": False,
        "money": False,
        "asset": args.asset,
        "timeframe": args.timeframe,
        "cycles": args.cycles,
        "started_at": now_iso(),
        "ended_at": None,
        "status": "RUNNING",
        "session_id": None,
        "agents": [],
    }

    agents = []

    agents.append(
        run_agent(
            "Compile Agent",
            [sys.executable, "-m", "compileall", "src", "scripts"],
        )
    )

    agents.append(
        run_agent(
            "Git Diff Check Agent",
            ["git", "diff", "--check"],
        )
    )

    agents.append(
        run_agent(
            "Trader DB Init Agent",
            [
                sys.executable,
                str(SCRIPTS_DIR / "predixai_trader_db_status.py"),
                "--init",
                "--json",
            ],
            expects_json=True,
        )
    )

    overnight = run_agent(
        "Overnight Observer Agent",
        [
            sys.executable,
            str(SCRIPTS_DIR / "predixai_overnight_observer.py"),
            "run",
            "--asset",
            args.asset,
            "--timeframe",
            args.timeframe,
            "--cycles",
            str(args.cycles),
            "--sleep-seconds",
            "0",
            "--synthetic",
            "--close-session",
            "--report-dir",
            str(RUNTIME_DIR / "overnight_observer"),
            "--json",
        ],
        expects_json=True,
    )
    agents.append(overnight)

    if overnight["json"]:
        report["session_id"] = overnight["json"].get("session_id")

    if report["session_id"] is not None:
        session_id = str(report["session_id"])

        agents.append(
            run_agent(
                "Market Session Audit Agent",
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "predixai_market_session.py"),
                    "get",
                    "--id",
                    session_id,
                    "--json",
                ],
                expects_json=True,
            )
        )

        agents.append(
            run_agent(
                "Triple RSI Observer Agent",
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "predixai_triple_rsi_observer.py"),
                    "calculate",
                    "--session-id",
                    session_id,
                    "--json",
                ],
                expects_json=True,
            )
        )

        agents.append(
            run_agent(
                "Triple Rebound Observer Agent",
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "predixai_triple_rebound_observer.py"),
                    "observe",
                    "--session-id",
                    session_id,
                    "--json",
                ],
                expects_json=True,
            )
        )
    else:
        print("[PTP-105] SESSION_ID não encontrado. RSI e Rebote foram pulados.")

    report["agents"] = agents
    report["ended_at"] = now_iso()

    failed_agents = [agent for agent in agents if agent["status"] != "PASS"]
    report["status"] = "PASS" if not failed_agents and report["session_id"] is not None else "FAIL"

    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_txt_report(report)

    print("\nPTP-105 — RELATÓRIO FINAL")
    print(f"STATUS={report['status']}")
    print(f"SESSION_ID={report['session_id']}")
    print(f"REPORT_JSON={REPORT_JSON}")
    print(f"REPORT_TXT={REPORT_TXT}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())