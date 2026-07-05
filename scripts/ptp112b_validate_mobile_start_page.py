from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "predixai" / "mobile" / "session_start_page.py"

spec = importlib.util.spec_from_file_location("session_start_page", PAGE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

html = module.render_mobile_session_start_page()

checks = {
    "titulo_predixai": "PredixAI Trader" in html,
    "modo_simulado": "Modo: SIMULADO" in html,
    "ordens_bloqueadas": "Ordens reais: BLOQUEADAS" in html,
    "sem_campo_corretora": "broker" not in html.lower() and "corretora" not in html.lower(),
    "sem_login": "login" not in html.lower(),
    "sem_senha": "senha" not in html.lower(),
    "sem_deposito": "depósito" in html.lower() and "deposit_enabled" not in html.lower(),
    "session_type": "session_type" in html,
    "strategy_mode": "strategy_mode" in html,
    "strategy_stack": "strategy_stack" in html,
    "min_confidence": "min_confidence" in html,
    "initial_bankroll": "initial_bankroll" in html,
    "initial_entry": "initial_entry" in html,
    "risk_profile": "risk_profile" in html,
    "stop_loss": "stop_loss" in html,
    "take_profit": "take_profit" in html,
    "max_signals": "max_signals" in html,
    "max_losses": "max_losses" in html,
    "payout_min": "payout_min" in html,
    "expiration_seconds": "expiration_seconds" in html,
    "recovery_enabled": "recovery_enabled" in html,
    "recovery_mode": "recovery_mode" in html,
    "max_recovery_steps": "max_recovery_steps" in html,
    "recovery_multiplier": "recovery_multiplier" in html,
    "confluence_required": "confluence_required" in html,
    "paper_trade_enabled": "paper_trade_enabled" in html,
    "max_open_trades_um": "max_open_trades" in html,
    "endpoint_start": "/mobile/session/start" in html,
}

passed = sum(1 for v in checks.values() if v)
failed = [k for k, v in checks.items() if not v]

print(f"PASS: {passed}")
print(f"FAIL: {len(failed)}")
for item in failed:
    print(f"FAILED: {item}")

if failed:
    raise SystemExit(1)
