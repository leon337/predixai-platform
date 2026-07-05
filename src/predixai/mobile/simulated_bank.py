from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Result = Literal["WIN", "LOSS", "DRAW"]
SessionStatus = Literal["active", "stop_loss", "take_profit", "max_losses", "closed"]


@dataclass
class SimulatedBankState:
    initial_bank: float
    current_bank: float
    entry_value: float
    stop_loss: float
    take_profit: float
    max_losses: int
    payout: float = 0.80
    operations: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    profit_loss: float = 0.0
    status: SessionStatus = "active"
    history: list[dict] = field(default_factory=list)

    @property
    def accuracy_rate(self) -> float:
        decided = self.wins + self.losses
        if decided <= 0:
            return 0.0
        return round((self.wins / decided) * 100, 2)

    @property
    def can_continue(self) -> bool:
        return self.status == "active"


class SimulatedBankEngine:
    """Motor de banca simulada para sessão mobile-first.

    Não acessa saldo real, não executa ordem, não clica em tela
    e não conversa com corretora. Apenas simula resultados.
    """

    def __init__(
        self,
        initial_bank: float,
        entry_value: float,
        stop_loss: float,
        take_profit: float,
        max_losses: int,
        payout: float = 0.80,
    ) -> None:
        self._validate_positive("initial_bank", initial_bank)
        self._validate_positive("entry_value", entry_value)
        self._validate_positive("stop_loss", stop_loss)
        self._validate_positive("take_profit", take_profit)

        if max_losses <= 0:
            raise ValueError("max_losses must be greater than zero")

        if payout <= 0:
            raise ValueError("payout must be greater than zero")

        self.state = SimulatedBankState(
            initial_bank=round(float(initial_bank), 2),
            current_bank=round(float(initial_bank), 2),
            entry_value=round(float(entry_value), 2),
            stop_loss=round(float(stop_loss), 2),
            take_profit=round(float(take_profit), 2),
            max_losses=int(max_losses),
            payout=round(float(payout), 4),
        )

    def apply_result(self, result: Result) -> SimulatedBankState:
        if not self.state.can_continue:
            return self.state

        result = result.upper()
        if result not in {"WIN", "LOSS", "DRAW"}:
            raise ValueError("result must be WIN, LOSS or DRAW")

        previous_bank = self.state.current_bank
        delta = 0.0

        if result == "WIN":
            delta = round(self.state.entry_value * self.state.payout, 2)
            self.state.wins += 1
        elif result == "LOSS":
            delta = -self.state.entry_value
            self.state.losses += 1
        else:
            self.state.draws += 1

        self.state.operations += 1
        self.state.current_bank = round(self.state.current_bank + delta, 2)
        self.state.profit_loss = round(self.state.current_bank - self.state.initial_bank, 2)

        self.state.history.append(
            {
                "operation": self.state.operations,
                "result": result,
                "previous_bank": round(previous_bank, 2),
                "delta": round(delta, 2),
                "current_bank": self.state.current_bank,
                "profit_loss": self.state.profit_loss,
                "status": self.state.status,
            }
        )

        self._refresh_status()
        self.state.history[-1]["status"] = self.state.status
        return self.state

    def close(self) -> SimulatedBankState:
        if self.state.status == "active":
            self.state.status = "closed"
        return self.state

    def snapshot(self) -> dict:
        return {
            "initial_bank": self.state.initial_bank,
            "current_bank": self.state.current_bank,
            "entry_value": self.state.entry_value,
            "stop_loss": self.state.stop_loss,
            "take_profit": self.state.take_profit,
            "max_losses": self.state.max_losses,
            "payout": self.state.payout,
            "operations": self.state.operations,
            "wins": self.state.wins,
            "losses": self.state.losses,
            "draws": self.state.draws,
            "profit_loss": self.state.profit_loss,
            "accuracy_rate": self.state.accuracy_rate,
            "status": self.state.status,
            "can_continue": self.state.can_continue,
            "history": list(self.state.history),
        }

    def _refresh_status(self) -> None:
        if self.state.profit_loss <= -self.state.stop_loss:
            self.state.status = "stop_loss"
        elif self.state.profit_loss >= self.state.take_profit:
            self.state.status = "take_profit"
        elif self.state.losses >= self.state.max_losses:
            self.state.status = "max_losses"

    @staticmethod
    def _validate_positive(name: str, value: float) -> None:
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")
