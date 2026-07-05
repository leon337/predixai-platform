from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass
class MobileSignalScreen:
    asset: str
    decision: str
    confidence: float
    confluence_level: str
    status: str
    session_status: str = "SIMULADA"
    bank_mode: str = "SIMULADO"
    generated_at: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

        self.asset = str(self.asset or "").strip()
        self.decision = str(self.decision or "").strip().upper()
        self.confluence_level = str(self.confluence_level or "").strip().upper()
        self.status = str(self.status or "").strip().upper()

        if not self.asset:
            raise ValueError("asset obrigatório")

        if self.decision not in {"ALTA", "BAIXA", "AGUARDAR"}:
            raise ValueError("decision inválida")

        if not 0 <= float(self.confidence) <= 95:
            raise ValueError("confidence fora da faixa permitida")

        if self.status not in {"APROVADO", "REJEITADO", "AGUARDAR"}:
            raise ValueError("status inválido")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_mobile_signal_screen(
    confluence_result: Mapping[str, Any] | Any,
    session_status: str = "SIMULADA",
    bank_mode: str = "SIMULADO",
) -> MobileSignalScreen:
    data = confluence_result.to_dict() if hasattr(confluence_result, "to_dict") else dict(confluence_result)
    decision = data.get("decision", data.get("strategy_decision", ""))

    if hasattr(decision, "to_dict"):
        decision = decision.to_dict()

    if isinstance(decision, Mapping):
        decision = decision.get("decision", "")

    return MobileSignalScreen(
        asset=data.get("asset", ""),
        decision=decision,
        confidence=float(data.get("confidence", data.get("final_confidence", 0))),
        confluence_level=data.get("confluence_level", data.get("level", "")),
        status=data.get("status", ""),
        session_status=session_status,
        bank_mode=bank_mode,
    )
