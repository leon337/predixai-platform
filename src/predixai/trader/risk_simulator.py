from __future__ import annotations

from typing import Any, Dict

from predixai.trader.recovery import RecoveryPlanner


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def simulate_pre_session(session_config, strategy_profile=None) -> Dict[str, Any]:
    """
    Simulação pré-sessão 100% simulada.
    """
    strategy_profile = strategy_profile or {}

    bankroll = max(1.0, float(_get(session_config, "simulated_bankroll", _get(session_config, "initial_bankroll", 100.0))))
    initial_entry = max(0.01, float(_get(session_config, "initial_entry", _get(session_config, "current_entry", 5.0))))
    stop = max(0.0, float(_get(session_config, "stop_loss", 20.0)))
    limit = max(1, int(_get(session_config, "signals_limit", _get(session_config, "max_signals", 10))))
    goal = float(_get(session_config, "session_goal", _get(session_config, "take_profit", 20.0)))
    recovery_mode = str(_get(session_config, "recovery_mode", "sem_recuperacao"))
    max_recovery_steps = int(_get(session_config, "max_recovery_steps", 0) or 0)
    payout = float(_get(session_config, "payout", _get(session_config, "payout_min", 80.0)))
    max_entry_limit = _get(session_config, "max_entry_limit", None)
    strategy_risk = _get(strategy_profile, "risk", _get(strategy_profile, "risk_level", "médio"))

    recovery_plan = RecoveryPlanner(
        mode=recovery_mode,
        max_steps=max_recovery_steps,
    ).build_plan(
        initial_entry=initial_entry,
        bankroll=bankroll,
        stop_loss=stop,
        max_entry_limit=max_entry_limit,
        payout=payout,
        strategy_risk=strategy_risk,
    )

    exposure_max = float(recovery_plan["exposure_max"])
    estimated_signals = max(1, min(limit, int(bankroll // max(1.0, initial_entry))))
    probable_time_minutes = estimated_signals * 5
    realistic_goal = goal <= bankroll * 2
    stop_supports_recovery = stop >= exposure_max if stop else False
    martingale_aggressive = recovery_plan["mode"].startswith("martingale")

    recommendation = "OK"
    if exposure_max > stop > 0:
        recommendation = "Reduzir exposição ou aumentar stop_loss"
    if recovery_plan["combined_risk"] == "ALTO":
        recommendation = "Reduzir entrada, limitar recuperação ou usar mão fixa"

    return {
        "risk_classification": recovery_plan["combined_risk"],
        "exposure_max": exposure_max,
        "max_entry": recovery_plan["max_entry"],
        "exposure_percent": recovery_plan["exposure_percent"],
        "entry_sequence": recovery_plan["entry_sequence"],
        "next_entry": recovery_plan["next_entry"],
        "estimated_signals": estimated_signals,
        "probable_time_minutes": probable_time_minutes,
        "realistic_goal": realistic_goal,
        "stop_supports_recovery": stop_supports_recovery,
        "martingale_aggressive": martingale_aggressive,
        "recommendation": recommendation,
        "recovery_plan": recovery_plan,
    }
