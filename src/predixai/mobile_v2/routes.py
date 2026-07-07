"""Clean Mobile V2 routes for PredixAI Trader.

These routes are intentionally minimal and controlled:
- They do not replace the legacy /mobile screen.
- They do not start a real observer process yet.
- They do not execute orders, clicks, broker login or real-money actions.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .state_store import RuntimeStateStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _with_runtime_fields(state: Dict[str, Any]) -> Dict[str, Any]:
    response_state = copy.deepcopy(state)
    reading = response_state.setdefault("reading", {})
    captured_at = _parse_iso(reading.get("captured_at"))

    if captured_at is None:
        reading["age_seconds"] = None
    else:
        reading["age_seconds"] = max(
            0.0,
            round((datetime.now(timezone.utc) - captured_at).total_seconds(), 3),
        )

    return response_state


def _route_exists(app: Any, rule: str) -> bool:
    try:
        return any(existing.rule == rule for existing in app.url_map.iter_rules())
    except Exception:
        return False


def _endpoint_exists(app: Any, endpoint: str) -> bool:
    return endpoint in getattr(app, "view_functions", {})


def register_mobile_v2_routes(app: Any, store: Optional[RuntimeStateStore] = None) -> Dict[str, Any]:
    """Register clean Mobile V2 routes on a Flask app.

    Returns a small registration report for auditability.
    """

    try:
        from flask import jsonify
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Flask is required to register Mobile V2 routes") from exc

    runtime_store = store or RuntimeStateStore()
    added = []
    skipped = []

    def add_rule(rule: str, endpoint: str, view_func: Any, methods: list[str]) -> None:
        if _endpoint_exists(app, endpoint) or _route_exists(app, rule):
            skipped.append({"rule": rule, "endpoint": endpoint})
            return
        app.add_url_rule(rule, endpoint, view_func, methods=methods)
        added.append({"rule": rule, "endpoint": endpoint, "methods": methods})

    def state_current():
        state = runtime_store.read_state()
        return jsonify(
            {
                "ok": True,
                "mobile_v2": True,
                "route": "/state/current",
                "state": _with_runtime_fields(state),
                "runtime_persisted": runtime_store.state_path.exists(),
                "note": "reading.age_seconds is calculated at response time and is not persisted.",
            }
        )

    def observer_start():
        now = _now_iso()

        def mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            state["status"] = "observer_waiting_source"
            state["observer"]["status"] = "ON_WAITING_SOURCE"
            state["observer"]["running"] = False
            state["observer"]["pid"] = None
            state["observer"]["last_error"] = None
            state["observer"]["started_at"] = now
            state["observer"]["stopped_at"] = None
            state["reading"]["status"] = "waiting_source"
            state["reading"]["source"] = "simulated_control_only"
            return state

        state = runtime_store.update_state(mutate)
        return jsonify(
            {
                "ok": True,
                "mobile_v2": True,
                "route": "/observer/start",
                "simulated_control_only": True,
                "reader_process_started": False,
                "message": "Observer V2 control state set to ON_WAITING_SOURCE. No real reader process was started.",
                "state": _with_runtime_fields(state),
            }
        )

    def observer_stop():
        now = _now_iso()

        def mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            state["status"] = "idle"
            state["observer"]["status"] = "OFF"
            state["observer"]["running"] = False
            state["observer"]["pid"] = None
            state["observer"]["last_error"] = None
            state["observer"]["stopped_at"] = now
            state["reading"]["status"] = "no_active_reading"
            state["reading"]["asset"] = None
            state["reading"]["price"] = None
            state["reading"]["captured_at"] = None
            state["reading"]["source"] = "none"
            state["signal"]["status"] = "aguardando_leitura"
            state["signal"]["direction"] = "NEUTRO"
            state["signal"]["confidence"] = None
            return state

        state = runtime_store.update_state(mutate)
        return jsonify(
            {
                "ok": True,
                "mobile_v2": True,
                "route": "/observer/stop",
                "simulated_control_only": True,
                "reader_process_stopped": False,
                "message": "Observer V2 control state set to OFF. No real process kill was executed.",
                "state": _with_runtime_fields(state),
            }
        )

    add_rule("/state/current", "mobile_v2_state_current", state_current, ["GET"])
    add_rule("/observer/start", "mobile_v2_observer_start", observer_start, ["POST"])
    add_rule("/observer/stop", "mobile_v2_observer_stop", observer_stop, ["POST"])

    return {
        "mobile_v2_routes": True,
        "added": added,
        "skipped": skipped,
        "simulated_control_only": True,
    }
