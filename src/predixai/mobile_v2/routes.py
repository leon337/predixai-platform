"""Clean Mobile V2 routes for PredixAI Trader.

These routes are intentionally controlled:
- They do not replace the legacy /mobile screen.
- They own only a deterministic simulation thread per application.
- They do not execute orders, clicks, broker login or real-money actions.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .observer_runtime import (
    APPLICATION_ID,
    DeterministicSimulatedSource,
    ObserverRuntimeController,
)
from .state_store import RuntimeStateStore


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


def register_mobile_v2_routes(
    app: Any,
    store: Optional[RuntimeStateStore] = None,
    *,
    observer_runtime: Optional[ObserverRuntimeController] = None,
    observer_source: Optional[Any] = None,
    observer_interval: float = 1.0,
    observer_clock: Optional[Any] = None,
    observer_event_factory: Optional[Any] = None,
) -> Dict[str, Any]:
    """Register clean Mobile V2 routes on a Flask app.

    Returns a small registration report for auditability.
    """

    try:
        from flask import jsonify
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Flask is required to register Mobile V2 routes") from exc

    runtime_store = store or RuntimeStateStore()
    existing_controller = app.extensions.get("observer_runtime")
    if existing_controller is not None:
        if observer_runtime is not None and observer_runtime is not existing_controller:
            raise ValueError("one Observer runtime controller is allowed per application")
        controller = existing_controller
    else:
        controller_kwargs: Dict[str, Any] = {
            "source": observer_source or DeterministicSimulatedSource(),
            "interval": observer_interval,
            "clock": observer_clock,
        }
        if observer_event_factory is not None:
            controller_kwargs["event_factory"] = observer_event_factory
        controller = observer_runtime or ObserverRuntimeController(
            runtime_store, **controller_kwargs
        )
        app.extensions["observer_runtime"] = controller
    if controller.store is not runtime_store:
        raise ValueError("Observer runtime and routes must share one state store")
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

    def observer_response(route: str, result: Dict[str, Any]):
        error = result["error"]
        payload = {
            "ok": error is None,
            "application_id": APPLICATION_ID,
            "mobile_v2": True,
            "route": route,
            "simulated_control_only": True,
            "reader_process_started": False,
            "reader_process_stopped": False,
            "observer_state": result["observer_state"],
            "observer_cycle": result["observer_cycle"],
            "changed": result["changed"],
            "error": error,
            "state": _with_runtime_fields(result["state"]),
        }
        return jsonify(payload), (200 if error is None else 409)

    def observer_start():
        return observer_response("/observer/start", controller.start())

    def observer_pause():
        return observer_response("/observer/pause", controller.pause())

    def observer_resume():
        return observer_response("/observer/resume", controller.resume())

    def observer_stop():
        return observer_response("/observer/stop", controller.stop())

    add_rule("/state/current", "mobile_v2_state_current", state_current, ["GET"])
    add_rule("/observer/start", "mobile_v2_observer_start", observer_start, ["POST"])
    add_rule("/observer/pause", "mobile_v2_observer_pause", observer_pause, ["POST"])
    add_rule("/observer/resume", "mobile_v2_observer_resume", observer_resume, ["POST"])
    add_rule("/observer/stop", "mobile_v2_observer_stop", observer_stop, ["POST"])

    return {
        "mobile_v2_routes": True,
        "added": added,
        "skipped": skipped,
        "simulated_control_only": True,
        "observer_runtime_extension": "observer_runtime",
    }
