"""OpenClaw local handoff runner.

PTP-086 foundation.
Safe local executor with an allowlist of commands.
This runner is intentionally limited:
- no commit
- no push
- no destructive commands
- no broker actions
- no screen clicks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class OpenClawRunner:
    """Run only allowlisted local commands and write a handoff report."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.openclaw_dir = self.repo_root / "tools" / "openclaw"
        self.allowlist_path = self.openclaw_dir / "allowlist.json"
        self.reports_dir = self.openclaw_dir / "reports"

    def load_allowlist(self) -> dict[str, Any]:
        return json.loads(self.allowlist_path.read_text(encoding="utf-8"))

    def list_tasks(self) -> list[str]:
        data = self.load_allowlist()
        return sorted(data.get("tasks", {}).keys())

    def run_task(self, task_name: str) -> Path:
        data = self.load_allowlist()
        tasks = data.get("tasks", {})
        if task_name not in tasks:
            available = ", ".join(sorted(tasks.keys()))
            raise SystemExit(f"Task not allowed: {task_name}. Available: {available}")

        task = tasks[task_name]
        commands = task.get("commands", [])
        if not isinstance(commands, list):
            raise SystemExit(f"Invalid command list for task: {task_name}")

        self.reports_dir.mkdir(parents=True, exist_ok=True)

        results: list[CommandResult] = []
        for command in commands:
            self._validate_command(command, data)
            results.append(self._run_command(command))

        report = {
            "runner": "OpenClaw",
            "ptp": data.get("ptp"),
            "task": task_name,
            "created_at": datetime.now().astimezone().isoformat(),
            "repo_root": str(self.repo_root),
            "policy": data.get("policy", {}),
            "results": [result.to_dict() for result in results],
        }

        report_path = self.reports_dir / f"openclaw_{task_name}_{self._timestamp()}.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path

    def _validate_command(self, command: Any, data: dict[str, Any]) -> None:
        if not isinstance(command, list) or not command:
            raise SystemExit(f"Invalid command format: {command!r}")

        command_text = " ".join(str(part) for part in command)
        blocked_patterns = data.get("blocked_patterns", [])
        for pattern in blocked_patterns:
            if pattern.lower() in command_text.lower():
                raise SystemExit(f"Blocked command pattern detected: {pattern}")

    def _run_command(self, command: list[str]) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            shell=False,
            check=False,
        )
        return CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw safe local runner")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--list", action="store_true", help="List allowed tasks")
    parser.add_argument("--task", help="Run an allowed task")
    args = parser.parse_args()

    runner = OpenClawRunner(Path(args.repo_root))

    if args.list:
        for task_name in runner.list_tasks():
            print(task_name)
        return 0

    if args.task:
        report_path = runner.run_task(args.task)
        print(f"OPENCLAW_REPORT={report_path}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
