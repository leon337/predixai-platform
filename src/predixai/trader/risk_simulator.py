from typing import Dict


def simulate_pre_session(session_config, strategy_profile) -> Dict:
    # Lightweight heuristics to estimate risks and exposures.
    bankroll = max(1.0, float(session_config.simulated_bankroll))
    stop = max(0.0, float(session_config.stop_loss))
    limit = max(1, int(session_config.signals_limit))

    exposure_max = min(bankroll, limit * session_config.initial_entry)
    estimated_signals = max(1, min(limit, int(bankroll // max(1.0, session_config.initial_entry))))
    probable_time_minutes = estimated_signals * 5

    # Simple realism checks
    realistic_goal = session_config.session_goal <= bankroll * 2
    stop_supports_recovery = stop < bankroll
    martingale_aggressive = session_config.recovery_mode.lower().startswith("martingale")

    # Risk classification
    risk_score = 0
    if exposure_max > bankroll * 0.5:
        risk_score += 2
    if session_config.initial_entry > bankroll * 0.2:
        risk_score += 2
    if session_config.signals_limit > 30:
        risk_score += 1

    if risk_score <= 1:
        classification = "BAIXO"
    elif risk_score == 2:
        classification = "MODERADO"
    else:
        classification = "ALTO"

    recommendation = "OK"
    if exposure_max > stop:
        recommendation = "Reduzir exposição ou aumentar stop_loss"

    return {
        "risk_classification": classification,
        "exposure_max": exposure_max,
        "estimated_signals": estimated_signals,
        "probable_time_minutes": probable_time_minutes,
        "realistic_goal": realistic_goal,
        "stop_supports_recovery": stop_supports_recovery,
        "martingale_aggressive": martingale_aggressive,
        "recommendation": recommendation,
    }
