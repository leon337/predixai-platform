from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


ALTA = "ALTA"
BAIXA = "BAIXA"
AGUARDAR = "AGUARDAR"

VALID_DECISIONS = {ALTA, BAIXA, AGUARDAR}


@dataclass(frozen=True)
class StrategyInput:
    asset: str
    current_price: float
    previous_price: float
    recent_prices: List[float] | None = None


@dataclass(frozen=True)
class StrategyDecision:
    decision: str
    confidence: float
    reason: str
    asset: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MinimalStrategyEngine:
    """
    Strategy Engine mínimo e seguro.

    Este motor apenas gera decisão simulada estruturada.
    Não executa ordem, não clica, não usa saldo real e não acessa corretora.
    """

    def analyze(self, data: StrategyInput) -> StrategyDecision:
        self._validate_input(data)

        delta = data.current_price - data.previous_price
        base_confidence = self._calculate_confidence(data)

        if delta > 0:
            decision = ALTA
            reason = "Preço atual acima do preço anterior."
        elif delta < 0:
            decision = BAIXA
            reason = "Preço atual abaixo do preço anterior."
        else:
            decision = AGUARDAR
            reason = "Preço sem variação suficiente para decisão."

        if base_confidence < 40:
            decision = AGUARDAR
            reason = "Confiança insuficiente para sinal direcional."

        return StrategyDecision(
            decision=decision,
            confidence=round(base_confidence, 2),
            reason=reason,
            asset=data.asset,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _validate_input(self, data: StrategyInput) -> None:
        if not data.asset or not data.asset.strip():
            raise ValueError("asset é obrigatório")
        if data.current_price <= 0:
            raise ValueError("current_price deve ser maior que zero")
        if data.previous_price <= 0:
            raise ValueError("previous_price deve ser maior que zero")

    def _calculate_confidence(self, data: StrategyInput) -> float:
        delta = abs(data.current_price - data.previous_price)
        relative_delta = delta / data.previous_price

        confidence = min(95.0, relative_delta * 10000)

        if data.recent_prices and len(data.recent_prices) >= 3:
            upward = data.recent_prices[-1] > data.recent_prices[0]
            downward = data.recent_prices[-1] < data.recent_prices[0]

            if upward or downward:
                confidence += 10.0

        return max(0.0, min(confidence, 95.0))
