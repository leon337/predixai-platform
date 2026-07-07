"""Standalone Flask app for PredixAI Mobile V2.

This app is intentionally separated from the legacy mobile server.
It exposes only Mobile V2 clean routes and does not start any real observer.
"""

from __future__ import annotations

from typing import Any, Optional

from flask import Flask, jsonify

from .routes import register_mobile_v2_routes
from .state_store import RuntimeStateStore


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
                "routes": [
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

    return app


__all__ = ["create_mobile_v2_app"]
