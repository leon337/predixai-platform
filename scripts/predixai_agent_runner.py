"""PredixAI supervised local OpenClaw agent runner."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_MODEL = "ollama/qwen2.5:1.5b"

DEFAULT_SMOKE_PROMPT = """Responda exatamente em texto puro.
Nao use JSON.
Nao chame ferramentas.
Nao escreva name nem arguments.

Resposta obrigatoria:
OK PREDIXAI AGENTE LOCAL ATIVO.
Ajudo o projeto PredixAI BR.
Respeito o modo V1 Observador.
Nao clico, nao opero, nao uso conta real e nao exijo API paga.
"""


def _looks_like_noise(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return True

    noisy_prefixes = (
        "openclaw : [agent/",
        "[agent/embedded]",
        "[agent]",
        "No linha:",
        "+ ",
        "    + CategoryInfo",
        "    + FullyQualifiedErrorId",
        "phase=",
        "cmd : ",
        "python : ",
    )

    if stripped.startswith(noisy_prefixes):
        return True

    if '"name"' in stripped and '"arguments"' in stripped:
        return True

    if stripped.startswith("{") and stripped.endswith("}"):
        return True

    return False


def clean_agent_output(raw_output: str) -> str:
    lines: list[str] = []

    for line in raw_output.splitlines():
        if _looks_like_noise(line):
            continue
        lines.append(line.strip())

    cleaned = "\n".join(line for line in lines if line).strip()

    marker = "OK PREDIXAI AGENTE LOCAL ATIVO."
    if marker in cleaned:
        cleaned = marker + cleaned.split(marker, 1)[1]

    return cleaned.strip()


def run_agent(prompt: str, model: str, timeout: int) -> tuple[int, str, str]:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="_predixai_agent_prompt.txt",
        delete=False,
    ) as prompt_file:
        prompt_file.write(prompt)
        prompt_path = Path(prompt_file.name)

    command = [
        "cmd",
        "/c",
        "openclaw",
        "agent",
        "--agent",
        "main",
        "--message-file",
        str(prompt_path),
        "--model",
        model,
        "--thinking",
        "off",
        "--local",
        "--timeout",
        str(timeout),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    raw_output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    clean_output = clean_agent_output(raw_output)

    try:
        prompt_path.unlink(missing_ok=True)
    except OSError:
        pass

    return completed.returncode, raw_output, clean_output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run PredixAI local OpenClaw agent with supervised output cleanup."
    )
    parser.add_argument("--message", help="Message to send to the local agent.")
    parser.add_argument("--message-file", help="UTF-8 text file with the message.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        prompt = DEFAULT_SMOKE_PROMPT
    elif args.message_file:
        prompt = Path(args.message_file).read_text(encoding="utf-8")
    elif args.message:
        prompt = args.message
    else:
        prompt = sys.stdin.read()

    returncode, raw_output, clean_output = run_agent(
        prompt=prompt,
        model=args.model,
        timeout=args.timeout,
    )

    if args.raw:
        print("===== RAW OPENCLAW OUTPUT =====")
        print(raw_output.strip())
        print("===== CLEAN OUTPUT =====")

    print(clean_output)

    if "OK PREDIXAI AGENTE LOCAL ATIVO." in clean_output:
        print("PREDIXAI_AGENT_WRAPPER_OK")
        return 0

    return returncode if returncode else 1


if __name__ == "__main__":
    raise SystemExit(main())
