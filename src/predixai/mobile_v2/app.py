"""Standalone Flask app for PredixAI Mobile V2.

Scope:
- Tela 1: /session/setup
- Tela 2: /mobile
- APIs clean: /state/current, /observer/start, /observer/stop
- No legacy mobile_server.py integration.
- No real observer, no real orders, no real money.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request

from .routes import register_mobile_v2_routes
from .state_store import RuntimeStateStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_brl_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    text = str(value).strip()
    if not text:
        return default

    text = text.replace("R$", "").replace(" ", "")

    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return default


def _session_payload_from_request() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form.to_dict()

    return {
        "initial_bank": _parse_brl_number(payload.get("initial_bank"), 100.0),
        "entry_value": _parse_brl_number(payload.get("entry_value"), 5.0),
        "profit_goal": _parse_brl_number(payload.get("profit_goal"), 10.0),
        "recovery_mode": str(payload.get("recovery_mode") or "sem_recuperacao"),
        "asset_label": str(payload.get("asset_label") or "Aguardando leitura"),
    }



# PTP113C83_CONTRATO_VISUAL_HELPERS_START
def _ptp113c83_money(value):
    try:
        if value is None or value == "":
            return "Não informado"
        number = float(value)
        return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(value)

def _ptp113c83_contract_view(state):
    state = state or {}
    config = state.get("config") or {}
    session = state.get("session") or {}
    reading = state.get("reading") or {}

    contract = session.get("contract")
    if not isinstance(contract, dict):
        contract = {}

    has_contract = bool(contract)

    return {
        "has_contract": has_contract,
        "session_status": session.get("status") if has_contract else "Nenhum contrato simulado ativo",
        "initial_bank": _ptp113c83_money(contract.get("initial_bank") or config.get("initial_bank")),
        "entry_value": _ptp113c83_money(contract.get("entry_value") or config.get("entry_value")),
        "profit_target": _ptp113c83_money(contract.get("profit_target") or config.get("profit_target")),
        "recovery_mode": contract.get("recovery_mode") or config.get("recovery_mode") or "Não informado",
        "observed_asset": reading.get("asset") or "Sem leitura ativa — Observer OFF",
        "signal_status": "Aguardando etapa C.8.5",
        "history_status": "Disponível na etapa C.8.6",
        "result_status": "Disponível na etapa C.8.7",
        "dynamic_balance_status": "Disponível na etapa C.8.7",
    }
# PTP113C83_CONTRATO_VISUAL_HELPERS_END


def create_mobile_v2_app(store: Optional[RuntimeStateStore] = None) -> Flask:
    """Create a standalone Mobile V2 Flask app."""
    app = Flask(__name__)
    runtime_store = store or RuntimeStateStore()

    registration = register_mobile_v2_routes(app, store=runtime_store)
    app.config["PREDIXAI_MOBILE_V2_ROUTE_REGISTRATION"] = registration

    @app.get("/")
    def mobile_v2_index() -> Any:
        return jsonify(
            {
                "ok": True,
                "app": "PredixAI Trader Mobile V2",
                "standalone": True,
                "legacy_mobile_server": False,
                "observer_real_started": False,
                "runtime_json_versioned": False,
                "screens": {
                    "setup": "/session/setup",
                    "mobile": "/mobile",
                },
                "routes": [
                    "GET /session/setup",
                    "POST /session/create",
                    "GET /mobile",
                    "GET /state/current",
                    "POST /observer/start",
                    "POST /observer/stop",
                    "GET /health",
                ],
                "safety": {
                    "simulation_only": True,
                    "orders_enabled": False,
                    "real_money_enabled": False,
                    "auto_click_enabled": False,
                    "broker_login_enabled": False,
                    "credentials_allowed": False,
                },
            }
        )

    @app.get("/health")
    def mobile_v2_health() -> Any:
        return jsonify(
            {
                "ok": True,
                "mobile_v2": True,
                "standalone": True,
                "legacy_mobile_server": False,
                "observer_real_started": False,
                "simulation_only": True,
            }
        )

    @app.get("/session/setup")
    def session_setup_screen() -> Any:
        return render_template("session_setup.html", contract_view=_ptp113c83_contract_view(store.read()))

    @app.post("/session/create")
    def session_create() -> Any:
        payload = _session_payload_from_request()
        now = _now_iso()

        def mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            state["status"] = "session_configured"
            session = state["session"]

            session["status"] = "configured"
            session["configured_at"] = now
            session["contract"] = {
                "initial_bank": payload["initial_bank"],
                "entry_value": payload["entry_value"],
                "profit_goal": payload["profit_goal"],
                "recovery_mode": payload["recovery_mode"],
                "asset_label": payload["asset_label"],
                "simulation_only": True,
            }

            session["simulation_only"] = True
            session["orders_enabled"] = False
            session["real_money_enabled"] = False
            session["auto_click_enabled"] = False
            session["broker_login_enabled"] = False
            session["credentials_allowed"] = False

            return state

        state = runtime_store.update_state(mutate)

        return jsonify(
            {
                "ok": True,
                "mobile_v2": True,
                "route": "/session/create",
                "simulated_contract_only": True,
                "signal_generation": False,
                "history_recording": False,
                "operation_result": False,
                "real_money": False,
                "state": state,
                "next_screen": "/mobile",
            }
        )

    @app.get("/mobile")
    def mobile_screen() -> Any:
        return render_template("mobile_v2_index.html", contract_view=_ptp113c83_contract_view(store.read()))

    return app


__all__ = ["create_mobile_v2_app"]
