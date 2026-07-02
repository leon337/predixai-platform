from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


ROOT_DIR = Path(__file__).resolve().parents[3]
RUNTIME_DIR = ROOT_DIR / "data" / "runtime"
LAST_READING_PATH = RUNTIME_DIR / "last_live_reading.json"
PRICE_HISTORY_PATH = RUNTIME_DIR / "live_price_history.json"
HISTORY_LIMIT = 3000

_reader_process: subprocess.Popen | None = None


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("D", "").replace("R$", "").replace("$", "").replace("%", "").strip()
    text = text.replace(" ", "")

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def _format_number(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 5)


def _normalize_point(point: dict[str, Any], index: int) -> dict[str, Any]:
    price_value = _as_float(point.get("price_value"))
    if price_value is None:
        price_value = _as_float(point.get("price"))

    return {
        "index": index,
        "timestamp": point.get("timestamp"),
        "asset": point.get("asset"),
        "price": point.get("price"),
        "price_value": _format_number(price_value),
        "payout": point.get("payout"),
        "balance": point.get("balance"),
        "trade_value": point.get("trade_value"),
        "duration": point.get("duration"),
        "remaining_time": point.get("remaining_time"),
        "expiration_suggestion": point.get("expiration_suggestion"),
        "timeframe": point.get("timeframe"),
        "confidence": point.get("confidence"),
        "status": point.get("status"),
    }


def _build_history_response() -> dict[str, Any]:
    raw_history = _read_json(PRICE_HISTORY_PATH, [])
    if not isinstance(raw_history, list):
        raw_history = []

    raw_history = raw_history[-HISTORY_LIMIT:]
    points = [
        _normalize_point(point, index)
        for index, point in enumerate(raw_history, start=1)
        if isinstance(point, dict)
    ]

    valid_prices = [
        point["price_value"]
        for point in points
        if isinstance(point.get("price_value"), (int, float))
    ]

    stats: dict[str, Any] = {
        "count": len(valid_prices),
        "total_points": len(points),
        "minimum": None,
        "maximum": None,
        "average": None,
        "amplitude": None,
        "first": None,
        "last": None,
        "variation": None,
        "variation_percent": None,
        "direction": "NO_DATA",
        "start_timestamp": points[0]["timestamp"] if points else None,
        "end_timestamp": points[-1]["timestamp"] if points else None,
        "asset": points[-1]["asset"] if points else None,
        "history_limit": HISTORY_LIMIT,
    }

    if valid_prices:
        first = valid_prices[0]
        last = valid_prices[-1]
        minimum = min(valid_prices)
        maximum = max(valid_prices)
        average = sum(valid_prices) / len(valid_prices)
        variation = last - first
        variation_percent = (variation / first * 100) if first else None

        if abs(variation) < 0.00001:
            direction = "LATERAL"
        elif variation > 0:
            direction = "UP"
        else:
            direction = "DOWN"

        stats.update(
            {
                "minimum": _format_number(minimum),
                "maximum": _format_number(maximum),
                "average": _format_number(average),
                "amplitude": _format_number(maximum - minimum),
                "first": _format_number(first),
                "last": _format_number(last),
                "variation": _format_number(variation),
                "variation_percent": _format_number(variation_percent),
                "direction": direction,
            }
        )

    return {"points": points, "stats": stats}


def _reader_running() -> bool:
    return _reader_process is not None and _reader_process.poll() is None


def _start_reader(interval: int) -> dict[str, Any]:
    global _reader_process

    if _reader_running():
        return {"status": "ALREADY_RUNNING", "interval": interval}

    env = os.environ.copy()
    src_path = str(ROOT_DIR / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable,
        "-m",
        "predixai.main",
        "--live-loop",
        "--loop-count",
        "9999",
        "--loop-interval",
        str(max(1, int(interval))),
    ]

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    _reader_process = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )

    return {"status": "STARTED", "interval": interval, "pid": _reader_process.pid}


def _stop_reader() -> dict[str, Any]:
    global _reader_process

    if _reader_running():
        _reader_process.terminate()
        return {"status": "STOPPED"}

    return {"status": "NOT_RUNNING"}


def create_dashboard_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    @app.after_request
    def add_no_cache_headers(response):  # type: ignore[no-untyped-def]
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    @app.route("/")
    def index():  # type: ignore[no-untyped-def]
        return render_template("index.html")

    @app.route("/api/last-reading")
    def last_reading():  # type: ignore[no-untyped-def]
        payload = _read_json(LAST_READING_PATH, {})
        if not isinstance(payload, dict) or not payload:
            return jsonify({"status": "NO_DATA"})
        return jsonify(payload)

    @app.route("/api/price-history")
    def price_history():  # type: ignore[no-untyped-def]
        return jsonify(_build_history_response())

    @app.route("/api/control/status")
    def control_status():  # type: ignore[no-untyped-def]
        return jsonify({"running": _reader_running()})

    @app.route("/api/control/start", methods=["POST"])
    def control_start():  # type: ignore[no-untyped-def]
        payload = request.get_json(silent=True) or {}
        interval = int(payload.get("interval", 3))
        return jsonify(_start_reader(interval))

    @app.route("/api/control/stop", methods=["POST"])
    def control_stop():  # type: ignore[no-untyped-def]
        return jsonify(_stop_reader())

    @app.route("/api/runtime/clear", methods=["POST"])
    def clear_runtime():  # type: ignore[no-untyped-def]
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        removed = []
        for path in RUNTIME_DIR.glob("*.json"):
            try:
                path.unlink()
                removed.append(path.name)
            except OSError:
                pass
        return jsonify({"status": "CLEARED", "removed": removed})

    return app


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    app = create_dashboard_app()
    url = f"http://{host}:{port}"

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"PredixAI dashboard running at {url}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


def run_dashboard_server() -> None:
    run_dashboard()


def launch_dashboard() -> None:
    run_dashboard()


def start_dashboard() -> None:
    run_dashboard()


run = run_dashboard
