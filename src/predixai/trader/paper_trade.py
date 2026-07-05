from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


VALID_DIRECTIONS = {"ALTA", "BAIXA", "AGUARDAR"}
VALID_STATUS = {"PENDING", "WIN", "LOSS", "DRAW", "SKIPPED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PaperTradeOperation:
    operation_id: str
    asset: str
    direction: str
    confidence: int
    entry_value: float
    status: str = "PENDING"
    result_value: Optional[float] = None
    opened_at: str = field(default_factory=_utc_now)
    closed_at: Optional[str] = None
    source: str = "MOBILE_SIMULATED_SESSION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "asset": self.asset,
            "direction": self.direction,
            "confidence": self.confidence,
            "entry_value": self.entry_value,
            "status": self.status,
            "result_value": self.result_value,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "source": self.source,
        }


@dataclass
class PaperTradeSession:
    session_id: str
    initial_balance: float = 100.0
    current_balance: float = 100.0
    operations: List[PaperTradeOperation] = field(default_factory=list)

    @property
    def operations_count(self) -> int:
        return len(self.operations)

    def open_operation(
        self,
        asset: str,
        direction: str,
        confidence: int,
        entry_value: float,
    ) -> PaperTradeOperation:
        direction = str(direction).upper().strip()

        if direction not in VALID_DIRECTIONS:
            raise ValueError("Direção inválida para Paper Trade simulado.")

        if direction == "AGUARDAR":
            raise ValueError("AGUARDAR não abre operação simulada.")

        if not 0 <= int(confidence) <= 95:
            raise ValueError("Confiança deve ficar entre 0 e 95.")

        if float(entry_value) <= 0:
            raise ValueError("Valor de entrada deve ser positivo.")

        operation = PaperTradeOperation(
            operation_id=str(uuid4()),
            asset=str(asset),
            direction=direction,
            confidence=int(confidence),
            entry_value=float(entry_value),
        )
        self.operations.append(operation)
        return operation

    def close_operation(
        self,
        operation_id: str,
        status: str,
        result_value: float = 0.0,
    ) -> PaperTradeOperation:
        status = str(status).upper().strip()

        if status not in VALID_STATUS:
            raise ValueError("Status inválido para Paper Trade simulado.")

        for operation in self.operations:
            if operation.operation_id == operation_id:
                operation.status = status
                operation.result_value = float(result_value)
                operation.closed_at = _utc_now()
                self.current_balance += float(result_value)
                return operation

        raise ValueError("Operação simulada não encontrada.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "operations": [op.to_dict() for op in self.operations],
            "operations_count": len(self.operations),
        }


def build_paper_trade_from_mobile_signal(
    mobile_signal: Any,
    session_id: str,
    entry_value: float = 5.0,
    initial_balance: float = 100.0,
) -> PaperTradeSession:
    data = mobile_signal.to_dict() if hasattr(mobile_signal, "to_dict") else dict(mobile_signal)

    session = PaperTradeSession(
        session_id=session_id,
        initial_balance=float(initial_balance),
        current_balance=float(initial_balance),
    )

    status = str(data.get("status", "")).upper()
    decision = str(data.get("decision", "")).upper()

    if status == "APROVADO" and decision in {"ALTA", "BAIXA"}:
        session.open_operation(
            asset=data.get("asset", "UNKNOWN"),
            direction=decision,
            confidence=int(data.get("confidence", 0)),
            entry_value=float(entry_value),
        )

    return session
