from typing import Dict


class RecoveryPlanner:
    MODES = [
        "sem_recuperacao",
        "mao_fixa",
        "soros",
        "martingale_1",
        "martingale_2",
        "martingale_3",
    ]

    def __init__(self, mode: str = "sem_recuperacao", max_steps: int = 3):
        if mode not in self.MODES:
            raise ValueError("Invalid recovery mode")
        self.mode = mode
        self.max_steps = max_steps

    def suggest_after_loss(self, last_entry: float, step: int = 1) -> Dict:
        # Returns the next suggested entry amount and a short rationale.
        if self.mode == "sem_recuperacao":
            return {"next_entry": 0.0, "reason": "Sem recuperação"}
        if self.mode == "mao_fixa":
            return {"next_entry": last_entry, "reason": "Manter entrada fixa"}
        if self.mode.startswith("martingale"):
            factor = 2 ** step
            return {"next_entry": last_entry * factor, "reason": f"Martingale x{factor}"}
        if self.mode == "soros":
            return {"next_entry": last_entry * 1.5, "reason": "Soros conservador"}
        return {"next_entry": 0.0, "reason": "Sem sugestão"}
