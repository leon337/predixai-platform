from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalStatus(Enum):
    AGUARDAR = "AGUARDAR"
    APROVADO_PARA_SIMULACAO = "APROVADO_PARA_SIMULACAO"
    BLOQUEADO = "BLOQUEADO"
    CANCELADO = "CANCELADO"
    DADO_INVALIDO = "DADO_INVALIDO"


@dataclass
class SignalCandidate:
    platform: str
    strategy: str
    asset: str
    direction: str
    current_price: float
    ideal_entry_price: Optional[float]
    breakout_price: Optional[float]
    cancel_price: Optional[float]
    best_entry_window: Optional[str]
    recommended_expiration: Optional[int]
    alternative_expiration: Optional[int]
    simulated_bankroll: float
    suggested_entry: float
    payout: Optional[float]
    expected_profit: Optional[float]
    session_goal: Optional[float]
    session_stop: Optional[float]
    recovery_mode: Optional[str]
    next_entry_on_loss: Optional[float]
    action_on_win: Optional[str]
    confidence: float = 0.0
    technical_reason: Optional[str] = None
    status: SignalStatus = SignalStatus.AGUARDAR

    def execute_real_order(self):
        raise RuntimeError("SignalCandidate cannot execute real orders in PTP-110")
