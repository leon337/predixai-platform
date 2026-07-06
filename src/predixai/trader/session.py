from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionConfig:
    platform: str
    access_type: str
    account_type: str
    strategy: Optional[str]
    simulated_bankroll: float
    initial_entry: float
    session_goal: float
    stop_loss: float
    signals_limit: int
    recovery_mode: str
    expiration: int
    save_evidence: bool = True
    executor_blocked: bool = True

    def validate(self) -> None:
        if not self.strategy:
            raise ValueError("Strategy must be defined before starting a session")
        if not self.executor_blocked:
            raise ValueError("Executor must remain blocked in PTP-110")
