"""
PTP-112F — Confluence Engine.

Camada de confirmação simulada para decisões do Strategy Engine.
Não executa ordens, não clica em tela, não usa saldo real e não acessa fonte externa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


VALID_STRATEGY_DECISIONS = {"ALTA", "BAIXA", "AGUARDAR"}
VALID_CONFLUENCE_STATUS = {"APROVADO", "REJEITADO", "AGUARDAR"}


@dataclass(frozen=True)
class ConfluenceResult:
    status: str
    level: str
    final_confidence: float
    reason: str
    asset: str
    strategy_decision: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "level": self.level,
            "final_confidence": self.final_confidence,
            "reason": self.reason,
            "asset": self.asset,
            "strategy_decision": self.strategy_decision,
            "timestamp": self.timestamp,
        }


class ConfluenceEngine:
    def __init__(self, minimum_confidence: float = 60.0) -> None:
        if minimum_confidence < 0 or minimum_confidence > 95:
            raise ValueError("minimum_confidence deve estar entre 0 e 95.")
        self.minimum_confidence = float(minimum_confidence)

    def evaluate(self, strategy_decision: Any) -> ConfluenceResult:
        data = self._normalize_strategy_decision(strategy_decision)

        decision = data["decision"]
        confidence = float(data["confidence"])
        asset = data["asset"]

        if decision == "AGUARDAR":
            return self._result(
                status="AGUARDAR",
                level="NEUTRA",
                final_confidence=confidence,
                reason="Confluência aguardando porque a estratégia não gerou direção operacional.",
                asset=asset,
                strategy_decision=decision,
            )

        if confidence < self.minimum_confidence:
            return self._result(
                status="REJEITADO",
                level="BAIXA",
                final_confidence=confidence,
                reason="Confluência rejeitada por confiança abaixo do mínimo definido.",
                asset=asset,
                strategy_decision=decision,
            )

        level = self._classify_level(confidence)
        return self._result(
            status="APROVADO",
            level=level,
            final_confidence=confidence,
            reason="Confluência aprovada por decisão direcional válida e confiança mínima atingida.",
            asset=asset,
            strategy_decision=decision,
        )

    def _normalize_strategy_decision(self, strategy_decision: Any) -> dict[str, Any]:
        if hasattr(strategy_decision, "to_dict"):
            data = strategy_decision.to_dict()
        elif isinstance(strategy_decision, dict):
            data = strategy_decision
        else:
            raise ValueError("strategy_decision deve ser dict ou objeto com to_dict().")

        required = {"decision", "confidence", "asset"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"strategy_decision sem campos obrigatórios: {sorted(missing)}")

        decision = str(data["decision"]).upper().strip()
        asset = str(data["asset"]).strip()

        if decision not in VALID_STRATEGY_DECISIONS:
            raise ValueError("decision inválida.")

        if not asset:
            raise ValueError("asset não pode ser vazio.")

        confidence = float(data["confidence"])
        if confidence < 0 or confidence > 95:
            raise ValueError("confidence deve estar entre 0 e 95.")

        return {
            "decision": decision,
            "confidence": confidence,
            "asset": asset,
        }

    def _classify_level(self, confidence: float) -> str:
        if confidence >= 80:
            return "ALTA"
        if confidence >= 60:
            return "MEDIA"
        return "BAIXA"

    def _result(
        self,
        status: str,
        level: str,
        final_confidence: float,
        reason: str,
        asset: str,
        strategy_decision: str,
    ) -> ConfluenceResult:
        if status not in VALID_CONFLUENCE_STATUS:
            raise ValueError("status de confluência inválido.")

        return ConfluenceResult(
            status=status,
            level=level,
            final_confidence=round(float(final_confidence), 2),
            reason=reason,
            asset=asset,
            strategy_decision=strategy_decision,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
