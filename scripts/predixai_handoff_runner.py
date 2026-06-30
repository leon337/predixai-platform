"""PredixAI handoff runner with strict semantic guardrail."""

from __future__ import annotations

import argparse
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "tools" / "openclaw" / "reports"


SAFE_FALLBACK = """OK PREDIXAI AGENTE LOCAL ATIVO.
Resposta original bloqueada pelo guardrail semantico do PredixAI BR.
Acao segura: manter o modo V1 Observador, gerar relatorio, validar evidencias e aguardar aprovacao do Leo.
Nao executo clique, ordem, conta real, automacao de corretora ou promessa de lucro.
Proximo passo: transformar a tarefa em checklist tecnico supervisionado."""


def safe_print(text: str) -> None:
    safe = str(text).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    try:
        print(safe)
    except UnicodeEncodeError:
        print(safe.encode("ascii", errors="replace").decode("ascii"))


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def repair_mojibake(text: str) -> str:
    variants = [text]
    for encoding in ("cp850", "cp437", "cp1252"):
        try:
            repaired = text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore")
            if repaired and repaired not in variants:
                variants.append(repaired)
        except Exception:
            pass
    return "\n".join(variants)


def normalize_text(text: str) -> str:
    repaired = repair_mojibake(text)
    normalized = unicodedata.normalize("NFKD", repaired)
    ascii_text = normalized.encode("ascii", errors="ignore").decode("ascii")
    return ascii_text.lower()


def forbidden_reason(text: str) -> str | None:
    t = normalize_text(text)

    if "tomada de decis" in t:
        return "decision_making_language"

    if "operac" in t:
        return "operation_language"

    if "transa" in t and "financeir" in t:
        return "financial_transactions"

    if "corretor" in t and any(word in t for word in ("configur", "selecione", "plataforma", "operar")):
        return "broker_setup"

    if ("compra" in t or "venda" in t) and "pagamento" in t:
        return "buy_sell_payment"

    if "implementar" in t and ("estrateg" in t or "transa" in t or "operac" in t):
        return "implementation_language"

    if "estrategia inicial" in t:
        return "strategy_implementation_language"

    if "conta real" in t and "nao" not in t:
        return "real_account_language"

    if "prometer lucro" in t and "nao" not in t:
        return "profit_promise_language"

    return None


def read_task(args: argparse.Namespace) -> str:
    if args.task_file:
        return Path(args.task_file).read_text(encoding="utf-8")
    if args.task:
        return args.task
    return sys.stdin.read()


def build_prompt(task: str) -> str:
    return f"""Responda em portugues do Brasil, sem acentos.

REGRA OBRIGATORIA:
Comece exatamente com:
OK PREDIXAI AGENTE LOCAL ATIVO.

Depois responda em no maximo 5 linhas.

Contexto:
Voce e o agente local PredixAI Architect.
Projeto: PredixAI BR.
Produto inicial: PredixAI Trader.
Modo atual: V1 Observador.

Limites absolutos:
Nao sugerir corretora.
Nao sugerir operacao financeira.
Nao sugerir compra, venda ou pagamento.
Nao clicar.
Nao operar conta real.
Nao executar ordens.
Nao prometer lucro.
Nao exigir API paga.
Nao alterar estrategia.
Nao falar em tomada de decisao.
Nao falar em operacoes.

Tarefa:
{task.strip()}
"""


def run_handoff(task: str, timeout: int) -> tuple[int, str, str, str | None, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    stamp = timestamp()
    prompt_path = REPORTS_DIR / f"predixai_handoff_prompt_{stamp}.txt"
    report_path = REPORTS_DIR / f"predixai_handoff_report_{stamp}.txt"

    prompt_path.write_text(build_prompt(task), encoding="utf-8")

    command = [
        "cmd",
        "/c",
        "scripts\\predixai_agent.bat",
        "--message-file",
        str(prompt_path),
        "--timeout",
        str(timeout),
    ]

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    raw_output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()

    reason = forbidden_reason(task + "\n" + raw_output)
    final_output = SAFE_FALLBACK if reason else raw_output

    report = "\n".join(
        [
            f"===== PREDIXAI HANDOFF REPORT - {stamp} =====",
            f"REPO={REPO_ROOT}",
            f"EXIT_CODE={completed.returncode}",
            f"SEMANTIC_GUARDRAIL_BLOCKED={bool(reason)}",
            f"SEMANTIC_GUARDRAIL_REASON={reason or 'none'}",
            "",
            "===== TASK =====",
            task.strip(),
            "",
            "===== FINAL OUTPUT =====",
            final_output,
            "",
            "===== RAW AGENT OUTPUT =====",
            raw_output,
            "",
            "===== END =====",
        ]
    )

    report_path.write_text(report, encoding="utf-8")
    return completed.returncode, raw_output, final_output, reason, report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="PredixAI supervised handoff runner.")
    parser.add_argument("--task", help="Task text.")
    parser.add_argument("--task-file", help="Task file path.")
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()

    task = read_task(args).strip()
    if not task:
        safe_print("PREDIXAI_HANDOFF_ERRO: tarefa vazia")
        return 2

    returncode, raw_output, final_output, reason, report_path = run_handoff(
        task=task,
        timeout=args.timeout,
    )

    safe_print(final_output)
    safe_print(f"PREDIXAI_HANDOFF_REPORT={report_path}")

    if reason:
        safe_print(f"PREDIXAI_HANDOFF_GUARDRAIL_APPLIED={reason}")

    if "ok predixai agente local ativo" in normalize_text(final_output):
        safe_print("PREDIXAI_HANDOFF_OK")
        return 0

    return returncode if returncode else 1


if __name__ == "__main__":
    raise SystemExit(main())
