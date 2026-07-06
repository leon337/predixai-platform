from typing import Dict


class RiskManager:
    def evaluate(self, signal, session_config, state: Dict = None) -> Dict:
        # Minimal checks returning decision and reason.
        state = state or {}
        reasons = []
        allowed = True

        if signal.confidence < 0.2:
            allowed = False
            reasons.append("confiança baixa")
        if signal.asset in (None, ""):
            allowed = False
            reasons.append("ativo inválido")
        if signal.payout is None or signal.payout <= 0:
            allowed = False
            reasons.append("payout ausente")
        if session_config.stop_loss <= 0:
            allowed = False
            reasons.append("stop_loss inválido")
        if session_config.signals_limit <= 0:
            allowed = False
            reasons.append("limite de sinais atingido")

        # Exposure rule
        exposure = signal.suggested_entry
        if exposure > session_config.stop_loss:
            allowed = False
            reasons.append("exposição maior que stop")

        return {"allowed": allowed, "reasons": reasons}
