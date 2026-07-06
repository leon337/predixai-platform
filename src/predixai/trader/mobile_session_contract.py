"""
PredixAI BR — PTP-112A
Mobile Session Contract v1.1

Contrato oficial da sessão mobile-first simulada.

Regras centrais:
- Sem ordem real.
- Sem clique automático.
- Sem login/corretora/senha no mobile.
- Sem dinheiro real.
- Saldo exibido = banca simulada.
- Segurança sempre forçada pelo servidor.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import uuid
from zoneinfo import ZoneInfo


CONTRACT_VERSION = "1.1"
SCHEMA_NAME = "MobileSessionContract"
SCHEMA_VERSION = "PTP-112A-v1.1"
DEFAULT_TIMEZONE = "America/Recife"

ALLOWED_STATUS = {
    "CREATED",
    "RUNNING",
    "PAUSED",
    "STOPPED",
    "FINISHED",
    "BLOCKED",
    "ERROR",
}

ALLOWED_SESSION_TYPES = {
    "SCALPER",
    "DAY_TRADE",
    "TEST",
    "TRAINING",
}

ALLOWED_STRATEGIES = {
    "LEGACY_MOMENTUM",
    "SUPPORT_RESISTANCE",
    "PRICE_ACTION",
    "CANDLE_REVERSAL",
}

FUTURE_BLOCKED_STRATEGIES = {
    "TRIPLE_REBOUND",
    "TRIPLE_RSI",
    "COMBINED_AI",
}

ALLOWED_RISK_PROFILES = {
    "CONSERVATIVE",
    "MODERATE",
    "AGGRESSIVE",
}

ALLOWED_RECOVERY_MODES = {
    "NONE",
    "FIXED",
    "MAO_FIXA",
    "SOROS",
    "SOFT_MARTINGALE",
    "MARTINGALE_1",
    "MARTINGALE_2",
    "SMARTGALE",
    "CUSTOM",
}

ALLOWED_PAYOUT_SOURCES = {
    "MANUAL",
    "AUTO_FUTURE",
    "UNKNOWN",
}

SECURITY_FIXED_VALUES = {
    "executor_blocked": True,
    "orders_enabled": False,
    "real_money_enabled": False,
    "auto_click_enabled": False,
    "broker_login_enabled": False,
    "deposit_enabled": False,
    "withdraw_enabled": False,
    "credentials_allowed": False,
}


def now_iso(timezone: str = DEFAULT_TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")


def new_session_id() -> str:
    stamp = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"mobile_{stamp}_{suffix}"


def default_mobile_session_contract() -> Dict[str, Any]:
    timestamp = now_iso()

    return {
        "session": {
            "contract_version": CONTRACT_VERSION,
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "session_id": new_session_id(),
            "created_at": timestamp,
            "updated_at": timestamp,
            "started_at": None,
            "ended_at": None,
            "timezone": DEFAULT_TIMEZONE,
            "created_by": "mobile",
            "environment": "LOCAL_SIMULATION",
            "status": "CREATED",
            "session_type": "SCALPER",
        },
        "config": {
            "asset_mode": "DETECTED_BY_READER",
            "broker_mode": "EXTERNAL_OPEN_WINDOW",
            "start_mode": "MOBILE_START",
            "session_notes": None,
        },
        "strategy": {
            "strategy_mode": "LEGACY_MOMENTUM",
            "strategy_stack": ["LEGACY_MOMENTUM"],
            "confluence_required": True,
            "min_confidence": 70,
            "strategy_locked": False,
        },
        "bankroll": {
            "currency": "BRL",
            "initial_bankroll": 100.0,
            "current_bankroll": 100.0,
            "initial_entry": 5.0,
            "current_entry": 5.0,
            "profit_loss": 0.0,
            "profit_loss_percent": 0.0,
        },
        "risk": {
            "risk_profile": "CONSERVATIVE",
            "stop_loss": 20.0,
            "take_profit": 20.0,
            "max_signals": 10,
            "max_losses": 3,
            "max_entry_limit": 20.0,
            "payout_min": 80,
            "payout_source": "MANUAL",
        },
        "operation": {
            "expiration_seconds": 60,
            "paper_trade_enabled": True,
            "signal_cooldown_seconds": 30,
            "allow_multiple_open_trades": False,
            "max_open_trades": 1,
        },
        "recovery": {
            "recovery_enabled": False,
            "recovery_mode": "NONE",
            "max_recovery_steps": 0,
            "current_recovery_step": 0,
            "recovery_multiplier": 1.0,
            "entry_sequence": [5.0],
            "next_entry": 5.0,
            "max_entry": 5.0,
            "exposure_max": 5.0,
            "exposure_percent": 5.0,
            "combined_risk": "BAIXO",
            "risk_alert": "Sem recuperação ativa.",
            "recovery_plan": {},
        },
        "security": deepcopy(SECURITY_FIXED_VALUES),
        "data_quality": {
            "require_valid_price": True,
            "require_active_window": True,
            "min_data_quality": 60,
            "allow_ignored_window": False,
            "allow_unknown_asset": True,
            "max_price_age_seconds": 10,
        },
        "preview": {
            "estimated_signals_5m": None,
            "estimated_signals_1h": None,
            "operational_profile": None,
            "risk_warning": None,
            "payout_warning": None,
            "recovery_warning": None,
            "session_feasibility": None,
        },
        "stats": {
            "signals_generated": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "canceled": 0,
            "win_rate": 0.0,
            "last_signal_id": None,
            "last_result": None,
        },
        "runtime": {
            "detected_asset": None,
            "active_window_title": None,
            "last_price": None,
            "last_price_at": None,
            "reader_status": None,
            "runtime_path": "data/runtime",
        },
        "safety_audit": {
            "security_locked_at": None,
            "security_source": "SERVER_ENFORCED",
            "blocked_reason": None,
            "last_validation_error": None,
            "last_validation_at": None,
        },
    }


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def enforce_server_security(contract: Dict[str, Any]) -> Dict[str, Any]:
    safe = deepcopy(contract)
    safe.setdefault("security", {})
    safe["security"].update(deepcopy(SECURITY_FIXED_VALUES))

    safe.setdefault("safety_audit", {})
    safe["safety_audit"]["security_source"] = "SERVER_ENFORCED"

    return safe


def build_mobile_session_contract(
    mobile_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    contract = default_mobile_session_contract()

    if mobile_config:
        contract = deep_merge(contract, mobile_config)

    contract = enforce_server_security(contract)
    contract["session"]["updated_at"] = now_iso(contract["session"].get("timezone", DEFAULT_TIMEZONE))
    contract = _ptp113b3151_enrich_contract_recovery_risk_v2(contract)

    return contract



# PTP-113B.3.1A.5.1_DYNAMIC_RECOVERY_RISK_V2
def _ptp113b3151_number_v2(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ptp113b3151_normalize_recovery_mode_v2(mode: Any) -> str:
    raw = str(mode or "NONE").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SEM_RECUPERACAO": "NONE",
        "SEM_RECUPERAÇÃO": "NONE",
        "FIXED": "MAO_FIXA",
        "MAO_FIXA": "MAO_FIXA",
        "MÃO_FIXA": "MAO_FIXA",
        "SOROS": "SOROS",
        "SOFT_MARTINGALE": "MARTINGALE_1",
        "MARTINGALE": "MARTINGALE_1",
        "MARTINGALE_1": "MARTINGALE_1",
        "MARTINGALE_2": "MARTINGALE_2",
        "SMARTGALE": "SMARTGALE",
        "CUSTOM": "SMARTGALE",
        "NONE": "NONE",
    }
    return aliases.get(raw, raw)


def _ptp113b3151_build_recovery_plan_v2(contract: Dict[str, Any]) -> Dict[str, Any]:
    bankroll = contract.get("bankroll", {})
    risk = contract.get("risk", {})
    recovery = contract.get("recovery", {})

    current_bankroll = _ptp113b3151_number_v2(bankroll.get("current_bankroll"), 100.0)
    initial_entry = _ptp113b3151_number_v2(bankroll.get("initial_entry"), 5.0)
    stop_loss = _ptp113b3151_number_v2(risk.get("stop_loss"), 20.0)
    max_entry_limit = _ptp113b3151_number_v2(risk.get("max_entry_limit"), min(stop_loss, current_bankroll))
    payout = _ptp113b3151_number_v2(risk.get("payout_min"), 80.0)

    enabled = bool(recovery.get("recovery_enabled", False))
    mode = _ptp113b3151_normalize_recovery_mode_v2(recovery.get("recovery_mode"))
    if not enabled:
        mode = "NONE"

    max_steps = int(_ptp113b3151_number_v2(recovery.get("max_recovery_steps"), 0))
    if mode == "MARTINGALE_1":
        max_steps = 1
    elif mode in {"MARTINGALE_2", "SMARTGALE"}:
        max_steps = 2
    elif mode == "SOROS":
        max_steps = max(1, min(max_steps or 2, 3))
    elif mode == "MAO_FIXA":
        max_steps = max(1, min(max_steps or 2, 5))
    elif mode == "NONE":
        max_steps = 0

    hard_cap = max(0.01, min(current_bankroll, stop_loss if stop_loss > 0 else current_bankroll, max_entry_limit if max_entry_limit > 0 else current_bankroll))

    if mode == "NONE":
        sequence = [initial_entry]
        reason = "Sem recuperação: entrada base mantida."
    elif mode == "MAO_FIXA":
        sequence = [initial_entry for _ in range(max_steps + 1)]
        reason = "Mão fixa: mesma entrada após perda."
    elif mode == "SOROS":
        sequence = [initial_entry]
        for _ in range(max_steps):
            sequence.append(sequence[-1] * 1.5)
        reason = "Soros/anti-martingale simulado."
    elif mode == "MARTINGALE_1":
        sequence = [initial_entry, initial_entry * 2]
        reason = "1 Martingale simulado."
    elif mode == "MARTINGALE_2":
        sequence = [initial_entry, initial_entry * 2, initial_entry * 4]
        reason = "2 Martingales simulados."
    elif mode == "SMARTGALE":
        sequence = [initial_entry, initial_entry * 1.6, initial_entry * 2.2]
        reason = "SmartGale simulado limitado por banca, stop e entrada máxima."
    else:
        sequence = [initial_entry]
        reason = "Modo tratado como entrada base."

    sequence = [round(min(max(0.01, value), hard_cap), 2) for value in sequence]
    exposure_max = round(sum(sequence), 2)
    max_entry = round(max(sequence), 2)
    next_entry = round(sequence[1] if len(sequence) > 1 else sequence[0], 2)
    exposure_percent = round((exposure_max / current_bankroll) * 100, 2) if current_bankroll else 0.0

    risk_score = 0
    if exposure_percent > 10:
        risk_score += 1
    if exposure_percent > 25:
        risk_score += 1
    if exposure_percent > 50:
        risk_score += 2
    if mode.startswith("MARTINGALE"):
        risk_score += 1
    if mode == "MARTINGALE_2":
        risk_score += 1
    if payout < 70:
        risk_score += 1
    if exposure_max > stop_loss > 0:
        risk_score += 2

    if risk_score <= 1:
        combined_risk = "BAIXO"
        alert = "Risco simulado baixo."
    elif risk_score <= 3:
        combined_risk = "MODERADO"
        alert = "Risco simulado moderado. Monitorar sequência de perdas."
    else:
        combined_risk = "ALTO"
        alert = "Risco simulado alto. Reduzir entrada ou recuperação."

    return {
        "mode": mode,
        "enabled": enabled,
        "max_recovery_steps": max_steps,
        "entry_sequence": sequence,
        "next_entry": next_entry,
        "max_entry": max_entry,
        "exposure_max": exposure_max,
        "exposure_percent": exposure_percent,
        "combined_risk": combined_risk,
        "risk_alert": alert,
        "reason": reason,
        "payout_reference": payout,
    }


def _ptp113b3151_enrich_contract_recovery_risk_v2(contract: Dict[str, Any]) -> Dict[str, Any]:
    safe = deepcopy(contract)
    safe.setdefault("risk", {})
    safe.setdefault("recovery", {})
    safe.setdefault("preview", {})

    plan = _ptp113b3151_build_recovery_plan_v2(safe)

    safe["risk"].setdefault("max_entry_limit", 20.0)
    safe["recovery"].update({
        "recovery_enabled": plan["enabled"],
        "recovery_mode": plan["mode"],
        "max_recovery_steps": plan["max_recovery_steps"],
        "entry_sequence": plan["entry_sequence"],
        "next_entry": plan["next_entry"],
        "max_entry": plan["max_entry"],
        "exposure_max": plan["exposure_max"],
        "exposure_percent": plan["exposure_percent"],
        "combined_risk": plan["combined_risk"],
        "risk_alert": plan["risk_alert"],
        "recovery_plan": plan,
    })

    safe["preview"]["recovery_warning"] = plan["risk_alert"]
    safe["preview"]["risk_warning"] = plan["combined_risk"]
    safe["preview"]["session_feasibility"] = "SIMULADA"

    return safe


def validate_mobile_session_contract(contract: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    required_blocks = {
        "session",
        "config",
        "strategy",
        "bankroll",
        "risk",
        "operation",
        "recovery",
        "security",
        "data_quality",
        "preview",
        "stats",
        "runtime",
        "safety_audit",
    }

    for block in required_blocks:
        if block not in contract or not isinstance(contract[block], dict):
            errors.append(f"Bloco ausente ou inválido: {block}")

    if errors:
        return False, errors

    session = contract["session"]
    strategy = contract["strategy"]
    bankroll = contract["bankroll"]
    risk = contract["risk"]
    operation = contract["operation"]
    recovery = contract["recovery"]
    security = contract["security"]
    data_quality = contract["data_quality"]

    if session.get("contract_version") != CONTRACT_VERSION:
        errors.append("contract_version inválido")

    if session.get("schema_name") != SCHEMA_NAME:
        errors.append("schema_name inválido")

    if session.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version inválido")

    if session.get("status") not in ALLOWED_STATUS:
        errors.append("status inválido")

    if session.get("session_type") not in ALLOWED_SESSION_TYPES:
        errors.append("session_type inválido")

    strategy_mode = strategy.get("strategy_mode")
    strategy_stack = strategy.get("strategy_stack")

    if strategy_mode in FUTURE_BLOCKED_STRATEGIES:
        errors.append("strategy_mode usa estratégia futura bloqueada")

    if strategy_mode not in ALLOWED_STRATEGIES:
        errors.append("strategy_mode inválido")

    if not isinstance(strategy_stack, list) or not strategy_stack:
        errors.append("strategy_stack deve ter pelo menos uma estratégia")
    else:
        blocked = [item for item in strategy_stack if item in FUTURE_BLOCKED_STRATEGIES]
        invalid = [item for item in strategy_stack if item not in ALLOWED_STRATEGIES]

        if blocked:
            errors.append(f"strategy_stack contém estratégias futuras bloqueadas: {blocked}")

        if invalid:
            errors.append(f"strategy_stack contém estratégias inválidas: {invalid}")

        if strategy_mode not in strategy_stack:
            errors.append("strategy_mode deve existir dentro de strategy_stack")

    if strategy.get("confluence_required") is not True:
        errors.append("confluence_required deve ser true")

    min_confidence = strategy.get("min_confidence")
    if not isinstance(min_confidence, (int, float)) or not 50 <= min_confidence <= 95:
        errors.append("min_confidence deve ficar entre 50 e 95")

    initial_bankroll = bankroll.get("initial_bankroll")
    current_bankroll = bankroll.get("current_bankroll")
    initial_entry = bankroll.get("initial_entry")
    current_entry = bankroll.get("current_entry")

    for name, value in {
        "initial_bankroll": initial_bankroll,
        "current_bankroll": current_bankroll,
        "initial_entry": initial_entry,
        "current_entry": current_entry,
    }.items():
        if not isinstance(value, (int, float)):
            errors.append(f"{name} deve ser numérico")

    if isinstance(initial_bankroll, (int, float)) and initial_bankroll <= 0:
        errors.append("initial_bankroll deve ser maior que zero")

    if isinstance(current_bankroll, (int, float)) and current_bankroll < 0:
        errors.append("current_bankroll não pode ser negativo")

    if (
        isinstance(initial_entry, (int, float))
        and isinstance(initial_bankroll, (int, float))
        and initial_entry > initial_bankroll
    ):
        errors.append("initial_entry não pode ser maior que initial_bankroll")

    if (
        isinstance(current_entry, (int, float))
        and isinstance(current_bankroll, (int, float))
        and current_entry > current_bankroll
    ):
        errors.append("current_entry não pode ser maior que current_bankroll")

    risk_profile = risk.get("risk_profile")
    if risk_profile not in ALLOWED_RISK_PROFILES:
        errors.append("risk_profile inválido")

    if isinstance(initial_entry, (int, float)) and isinstance(initial_bankroll, (int, float)):
        exposure_percent = (initial_entry / initial_bankroll) * 100

        if risk_profile == "CONSERVATIVE" and exposure_percent > 10:
            errors.append("CONSERVATIVE não permite entrada inicial acima de 10% da banca")

        if risk_profile == "MODERATE" and exposure_percent > 20:
            errors.append("MODERATE não permite entrada inicial acima de 20% da banca")

        if risk_profile == "AGGRESSIVE" and exposure_percent > 30:
            errors.append("AGGRESSIVE não permite entrada inicial acima de 30% da banca")

    stop_loss = risk.get("stop_loss")
    take_profit = risk.get("take_profit")
    payout_min = risk.get("payout_min")
    max_entry_limit = risk.get("max_entry_limit")

    if not isinstance(stop_loss, (int, float)) or stop_loss <= 0:
        errors.append("stop_loss deve ser maior que zero")

    if not isinstance(take_profit, (int, float)) or take_profit <= 0:
        errors.append("take_profit deve ser maior que zero")

    if isinstance(stop_loss, (int, float)) and isinstance(initial_bankroll, (int, float)):
        if stop_loss > initial_bankroll:
            errors.append("stop_loss não pode ser maior que initial_bankroll")

    if not isinstance(payout_min, (int, float)) or not 50 <= payout_min <= 100:
        errors.append("payout_min deve ficar entre 50 e 100")

    if max_entry_limit is not None:
        if not isinstance(max_entry_limit, (int, float)) or max_entry_limit <= 0:
            errors.append("max_entry_limit deve ser maior que zero")
        elif isinstance(initial_bankroll, (int, float)) and max_entry_limit > initial_bankroll:
            errors.append("max_entry_limit não pode ser maior que initial_bankroll")

    if risk.get("payout_source") not in ALLOWED_PAYOUT_SOURCES:
        errors.append("payout_source inválido")

    max_signals = risk.get("max_signals")
    max_losses = risk.get("max_losses")

    if not isinstance(max_signals, int) or not 1 <= max_signals <= 100:
        errors.append("max_signals deve ficar entre 1 e 100")

    if not isinstance(max_losses, int) or not 1 <= max_losses <= 20:
        errors.append("max_losses deve ficar entre 1 e 20")

    expiration = operation.get("expiration_seconds")
    if not isinstance(expiration, int) or not 30 <= expiration <= 3600:
        errors.append("expiration_seconds deve ficar entre 30 e 3600")

    if operation.get("paper_trade_enabled") is not True:
        errors.append("paper_trade_enabled deve ser true")

    if operation.get("allow_multiple_open_trades") is not False:
        errors.append("allow_multiple_open_trades deve ser false nesta fase")

    if operation.get("max_open_trades") != 1:
        errors.append("max_open_trades deve ser 1 nesta fase")

    recovery_enabled = recovery.get("recovery_enabled")
    recovery_mode = recovery.get("recovery_mode")
    max_recovery_steps = recovery.get("max_recovery_steps")
    current_recovery_step = recovery.get("current_recovery_step")
    recovery_multiplier = recovery.get("recovery_multiplier")

    if recovery_mode not in ALLOWED_RECOVERY_MODES:
        errors.append("recovery_mode inválido")

    if recovery_enabled is False:
        if recovery_mode != "NONE":
            errors.append("recovery_mode deve ser NONE quando recovery_enabled=false")
        if max_recovery_steps != 0:
            errors.append("max_recovery_steps deve ser 0 quando recovery_enabled=false")

    if not isinstance(max_recovery_steps, int) or not 0 <= max_recovery_steps <= 5:
        errors.append("max_recovery_steps deve ficar entre 0 e 5")

    if not isinstance(current_recovery_step, int) or not 0 <= current_recovery_step <= 5:
        errors.append("current_recovery_step deve ficar entre 0 e 5")

    if current_recovery_step > max_recovery_steps:
        errors.append("current_recovery_step não pode ser maior que max_recovery_steps")

    if not isinstance(recovery_multiplier, (int, float)) or not 1.0 <= recovery_multiplier <= 3.0:
        errors.append("recovery_multiplier deve ficar entre 1.0 e 3.0")

    for key, expected in SECURITY_FIXED_VALUES.items():
        if security.get(key) is not expected:
            errors.append(f"security.{key} deve ser {expected}")

    if data_quality.get("allow_ignored_window") is not False:
        errors.append("allow_ignored_window deve ser false")

    min_data_quality = data_quality.get("min_data_quality")
    if not isinstance(min_data_quality, (int, float)) or not 0 <= min_data_quality <= 100:
        errors.append("min_data_quality deve ficar entre 0 e 100")

    max_price_age_seconds = data_quality.get("max_price_age_seconds")
    if not isinstance(max_price_age_seconds, int) or max_price_age_seconds <= 0:
        errors.append("max_price_age_seconds deve ser inteiro maior que zero")

    return len(errors) == 0, errors


def mark_contract_blocked(
    contract: Dict[str, Any],
    reason: str,
    validation_error: Optional[str] = None,
) -> Dict[str, Any]:
    blocked = deepcopy(contract)
    timestamp = now_iso(blocked.get("session", {}).get("timezone", DEFAULT_TIMEZONE))

    blocked.setdefault("session", {})
    blocked["session"]["status"] = "BLOCKED"
    blocked["session"]["updated_at"] = timestamp

    blocked.setdefault("safety_audit", {})
    blocked["safety_audit"]["security_locked_at"] = timestamp
    blocked["safety_audit"]["blocked_reason"] = reason
    blocked["safety_audit"]["last_validation_error"] = validation_error
    blocked["safety_audit"]["last_validation_at"] = timestamp

    return enforce_server_security(blocked)


def save_mobile_session_contract(contract: Dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def load_mobile_session_contract(path: str | Path) -> Dict[str, Any]:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8"))


__all__ = [
    "CONTRACT_VERSION",
    "SCHEMA_NAME",
    "SCHEMA_VERSION",
    "SECURITY_FIXED_VALUES",
    "default_mobile_session_contract",
    "build_mobile_session_contract",
    "validate_mobile_session_contract",
    "enforce_server_security",
    "mark_contract_blocked",
    "save_mobile_session_contract",
    "load_mobile_session_contract",
]
