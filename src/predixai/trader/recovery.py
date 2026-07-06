from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RecoveryPlan:
    mode: str
    enabled: bool
    entry_sequence: List[float]
    next_entry: float
    max_entry: float
    exposure_max: float
    exposure_percent: float
    combined_risk: str
    risk_alert: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "entry_sequence": self.entry_sequence,
            "next_entry": self.next_entry,
            "max_entry": self.max_entry,
            "exposure_max": self.exposure_max,
            "exposure_percent": self.exposure_percent,
            "combined_risk": self.combined_risk,
            "risk_alert": self.risk_alert,
            "reason": self.reason,
        }


class RecoveryPlanner:
    """
    Planejador de recuperação 100% simulado.
    Não executa ordem, não clica, não usa saldo real.
    """

    MODES = [
        "sem_recuperacao",
        "none",
        "fixed",
        "mao_fixa",
        "mão_fixa",
        "soros",
        "martingale_1",
        "martingale_2",
        "smartgale",
    ]

    MODE_ALIASES = {
        "NONE": "sem_recuperacao",
        "SEM_RECUPERACAO": "sem_recuperacao",
        "SEM_RECUPERAÇÃO": "sem_recuperacao",
        "FIXED": "mao_fixa",
        "MAO_FIXA": "mao_fixa",
        "MÃO_FIXA": "mao_fixa",
        "SOROS": "soros",
        "SOFT_MARTINGALE": "martingale_1",
        "MARTINGALE": "martingale_1",
        "MARTINGALE_1": "martingale_1",
        "MARTINGALE_2": "martingale_2",
        "SMARTGALE": "smartgale",
        "CUSTOM": "smartgale",
    }

    def __init__(self, mode: str = "sem_recuperacao", max_steps: int = 0):
        normalized = self.normalize_mode(mode)
        if normalized not in self.MODES:
            raise ValueError(f"Invalid recovery mode: {mode}")
        self.mode = normalized
        self.max_steps = max(0, int(max_steps or 0))

    @classmethod
    def normalize_mode(cls, mode: str | None) -> str:
        raw = str(mode or "sem_recuperacao").strip()
        upper = raw.upper().replace("-", "_").replace(" ", "_")
        return cls.MODE_ALIASES.get(upper, raw.lower())

    def suggest_after_loss(self, last_entry: float, step: int = 1) -> Dict[str, Any]:
        entry = max(0.0, float(last_entry or 0.0))
        step = max(1, int(step or 1))

        if self.mode in {"sem_recuperacao", "none"}:
            return {"next_entry": 0.0, "reason": "Sem recuperação"}

        if self.mode in {"mao_fixa", "mão_fixa", "fixed"}:
            return {"next_entry": round(entry, 2), "reason": "Manter entrada fixa"}

        if self.mode == "martingale_1":
            return {"next_entry": round(entry * 2, 2), "reason": "1 Martingale simulado"}

        if self.mode == "martingale_2":
            factor = 2 if step <= 1 else 4
            return {"next_entry": round(entry * factor, 2), "reason": f"2 Martingales simulados — nível {min(step, 2)}"}

        if self.mode == "soros":
            return {"next_entry": round(entry * 1.5, 2), "reason": "Soros conservador simulado"}

        if self.mode == "smartgale":
            factor = 1.6 if step <= 1 else 2.2
            return {"next_entry": round(entry * factor, 2), "reason": "SmartGale simulado com progressão limitada"}

        return {"next_entry": 0.0, "reason": "Sem sugestão"}

    def build_plan(
        self,
        initial_entry: float,
        bankroll: float,
        stop_loss: float,
        max_entry_limit: float | None = None,
        payout: float = 80.0,
        strategy_risk: str = "médio",
    ) -> Dict[str, Any]:
        entry = max(0.01, float(initial_entry or 0.01))
        bankroll = max(0.01, float(bankroll or 0.01))
        stop_loss = max(0.0, float(stop_loss or 0.0))
        payout = max(0.0, float(payout or 0.0))

        caps = [bankroll]
        if stop_loss > 0:
            caps.append(stop_loss)
        if max_entry_limit is not None and float(max_entry_limit or 0) > 0:
            caps.append(float(max_entry_limit))
        hard_cap = max(0.01, min(caps))

        enabled = self.mode not in {"sem_recuperacao", "none"}
        max_steps = self.max_steps if enabled else 0

        if self.mode in {"sem_recuperacao", "none"}:
            sequence = [entry]
            reason = "Sem recuperação: entrada base mantida."
        elif self.mode in {"mao_fixa", "mão_fixa", "fixed"}:
            sequence = [entry for _ in range(max_steps + 1)]
            reason = "Mão fixa: mesma entrada após perda."
        elif self.mode == "soros":
            sequence = [entry]
            for _ in range(max_steps):
                sequence.append(sequence[-1] * 1.5)
            reason = "Soros/anti-martingale: progressão simulada conservadora."
        elif self.mode == "martingale_1":
            sequence = [entry, entry * 2]
            reason = "1 Martingale: uma tentativa simulada de recuperação."
        elif self.mode == "martingale_2":
            sequence = [entry, entry * 2, entry * 4]
            reason = "2 Martingales: duas tentativas simuladas de recuperação."
        elif self.mode == "smartgale":
            sequence = [entry, entry * 1.6, entry * 2.2]
            reason = "SmartGale: progressão simulada limitada por banca, stop e entrada máxima."
        else:
            sequence = [entry]
            reason = "Modo desconhecido tratado como entrada base."

        sequence = [round(min(max(0.01, value), hard_cap), 2) for value in sequence]
        exposure_max = round(sum(sequence), 2)
        max_entry = round(max(sequence), 2)
        next_entry = round(sequence[1] if len(sequence) > 1 else sequence[0], 2)
        exposure_percent = round((exposure_max / bankroll) * 100, 2)

        risk_score = 0
        if exposure_percent > 10:
            risk_score += 1
        if exposure_percent > 25:
            risk_score += 1
        if exposure_percent > 50:
            risk_score += 2
        if self.mode.startswith("martingale"):
            risk_score += 1
        if self.mode == "martingale_2":
            risk_score += 1
        if payout < 70:
            risk_score += 1
        if "alto" in str(strategy_risk).lower():
            risk_score += 1
        if stop_loss and exposure_max > stop_loss:
            risk_score += 2

        if risk_score <= 1:
            combined_risk = "BAIXO"
            alert = "Risco simulado baixo, dentro dos limites básicos."
        elif risk_score <= 3:
            combined_risk = "MODERADO"
            alert = "Risco simulado moderado. Monitorar exposição e sequência de perdas."
        else:
            combined_risk = "ALTO"
            alert = "Risco simulado alto. Reduzir entrada, recuperação ou stop."

        return RecoveryPlan(
            mode=self.mode,
            enabled=enabled,
            entry_sequence=sequence,
            next_entry=next_entry,
            max_entry=max_entry,
            exposure_max=exposure_max,
            exposure_percent=exposure_percent,
            combined_risk=combined_risk,
            risk_alert=alert,
            reason=reason,
        ).to_dict()
