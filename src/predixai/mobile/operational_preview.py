"""PTP-112C — Operational Preview Engine.

Calcula uma prévia operacional simulada antes da sessão mobile.
Não acessa corretora, não executa ordem e não altera banca.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class OperationalPreview:
    profile: str
    risk_index: int
    estimated_signals_5m: int
    estimated_signals_hour: int
    scalper_compatible: bool
    day_trade_compatible: bool
    expected_exposure: float
    stop_supported: bool
    recovery_risk: str
    payout_impact: str
    alerts: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_operational_preview(config: Dict[str, Any]) -> Dict[str, Any]:
    strategy_mode = str(config.get("strategy_mode", "balanced")).lower()
    risk_profile = str(config.get("risk_profile", "moderate")).lower()

    min_confidence = _num(config.get("min_confidence"), 0.70)
    bankroll = _num(config.get("initial_bankroll"), 100.0)
    entry = _num(config.get("initial_entry"), 5.0)
    stop_loss = _num(config.get("stop_loss"), 20.0)
    take_profit = _num(config.get("take_profit"), 20.0)
    max_signals = int(_num(config.get("max_signals"), 10))
    max_losses = int(_num(config.get("max_losses"), 3))
    payout_min = _num(config.get("payout_min"), 0.80)
    expiration = int(_num(config.get("expiration_seconds"), 60))
    recovery_enabled = bool(config.get("recovery_enabled", False))
    recovery_multiplier = _num(config.get("recovery_multiplier"), 2.0)
    max_recovery_steps = int(_num(config.get("max_recovery_steps"), 0))

    base_hour = 12
    if strategy_mode == "scalper":
        base_hour = 24
    elif strategy_mode == "day_trade":
        base_hour = 6

    if min_confidence >= 0.85:
        base_hour = int(base_hour * 0.55)
    elif min_confidence <= 0.65:
        base_hour = int(base_hour * 1.25)

    if payout_min >= 0.90:
        base_hour = int(base_hour * 0.70)

    estimated_hour = max(1, min(max_signals, base_hour))
    estimated_5m = max(1, round(estimated_hour / 12))

    exposure = entry * max(1, min(max_losses, max_signals))
    if recovery_enabled:
        recovery_sum = sum(entry * (recovery_multiplier ** step) for step in range(max_recovery_steps + 1))
        exposure = max(exposure, recovery_sum)

    exposure_pct = 100.0 if bankroll <= 0 else round((exposure / bankroll) * 100, 2)

    risk_score = 20
    risk_score += 20 if risk_profile == "aggressive" else 10 if risk_profile == "moderate" else 0
    risk_score += 20 if recovery_enabled else 0
    risk_score += 15 if exposure_pct > 30 else 8 if exposure_pct > 15 else 0
    risk_score += 10 if min_confidence < 0.70 else 0
    risk_score += 10 if payout_min < 0.75 else 0
    risk_score = min(100, risk_score)

    profile = "Conservadora" if risk_score <= 35 else "Moderada" if risk_score <= 65 else "Agressiva"

    alerts: List[str] = []
    recommendations: List[str] = []

    stop_supported = stop_loss >= exposure
    if not stop_supported:
        alerts.append("Stop Loss menor que a exposição prevista.")
        recommendations.append("Reduzir entrada, perdas máximas ou recuperação.")

    if estimated_hour <= 3:
        alerts.append("Configuração pode gerar poucos sinais.")
        recommendations.append("Reduzir confiança mínima ou payout mínimo, se fizer sentido.")

    if estimated_hour >= 20:
        alerts.append("Configuração pode gerar sinais em excesso.")
        recommendations.append("Aumentar confiança mínima ou reduzir limite de sinais.")

    if recovery_enabled and max_recovery_steps >= 2:
        alerts.append("Recuperação aumenta a exposição da banca.")
        recommendations.append("Validar recuperação somente em modo simulado.")

    if entry > bankroll * 0.10:
        alerts.append("Entrada inicial acima de 10% da banca simulada.")
        recommendations.append("Usar entrada menor para preservar a sessão.")

    scalper_compatible = expiration <= 120 and estimated_hour >= 8
    day_trade_compatible = expiration >= 300 or strategy_mode == "day_trade"

    recovery_risk = "alto" if recovery_enabled and max_recovery_steps >= 2 else "moderado" if recovery_enabled else "baixo"
    payout_impact = "restritivo" if payout_min >= 0.90 else "moderado" if payout_min >= 0.80 else "flexível"

    preview = OperationalPreview(
        profile=profile,
        risk_index=risk_score,
        estimated_signals_5m=estimated_5m,
        estimated_signals_hour=estimated_hour,
        scalper_compatible=scalper_compatible,
        day_trade_compatible=day_trade_compatible,
        expected_exposure=round(exposure, 2),
        stop_supported=stop_supported,
        recovery_risk=recovery_risk,
        payout_impact=payout_impact,
        alerts=alerts,
        recommendations=recommendations,
    )

    return preview.to_dict()
