from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryPlan:
    ideal_entry_price: Optional[float]
    breakout_price: Optional[float]
    cancel_price: Optional[float]
    best_entry_window: Optional[str]
    recommended_expiration: Optional[int]
    alternative_expiration: Optional[int]
    technical_reason: Optional[str]


def generate_entry_plan(signal) -> EntryPlan:
    # Minimal, deterministic plan based on provided signal fields.
    ideal = signal.ideal_entry_price or signal.current_price
    breakout = signal.breakout_price or (ideal * 1.01 if signal.direction.lower() == "call" else ideal * 0.99)
    cancel = signal.cancel_price or (ideal * 0.995 if signal.direction.lower() == "call" else ideal * 1.005)
    best_window = signal.best_entry_window or "IMMEDIATE"
    rec_exp = signal.recommended_expiration or 60
    alt_exp = signal.alternative_expiration or max(10, rec_exp // 2)
    reason = signal.technical_reason or "Plano gerado automaticamente"
    return EntryPlan(
        ideal_entry_price=ideal,
        breakout_price=breakout,
        cancel_price=cancel,
        best_entry_window=best_window,
        recommended_expiration=rec_exp,
        alternative_expiration=alt_exp,
        technical_reason=reason,
    )
