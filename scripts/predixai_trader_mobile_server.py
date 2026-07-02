# -*- coding: utf-8 -*-
"""
PredixAI Trader Mobile Server.

Servidor local observador/simulado para acompanhar o Trader pelo celular.
Nao clica, nao executa ordens e nao interage com conta real.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from flask import Flask, jsonify, request
    HAS_FLASK = True
except ImportError:  # pragma: no cover - runtime fallback for local setup
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    HAS_FLASK = False


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
RUNTIME_DIR = ROOT_DIR / "data" / "runtime"
LAST_READING_PATH = RUNTIME_DIR / "last_live_reading.json"
PRICE_HISTORY_PATH = RUNTIME_DIR / "live_price_history.json"
REJECTED_READINGS_PATH = RUNTIME_DIR / "rejected_live_readings.json"
SIGNALS_DB_PATH = RUNTIME_DIR / "predixai_trader_signals.db"

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
HISTORY_LIMIT = 60
SIGNALS_LIMIT = 20
SIGNAL_COOLDOWN_SECONDS = 60
DEFAULT_EXPIRATION_SECONDS = 60

OBSERVATION_NOTICE = "Modo observador. Não é recomendação financeira."
SIMULATION_NOTICE = "Modo observador/simulado. Não executa ordens."

_reader_process: subprocess.Popen | None = None
_reader_interval: int | None = None


MOBILE_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>PredixAI Trader Mobile</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #061018;
      --panel: #101b28;
      --panel-2: #0b1622;
      --line: #00e5ff;
      --text: #f5f7fb;
      --muted: #a8b5c6;
      --green: #38d66b;
      --yellow: #ffbf00;
      --red: #ff4d6d;
      --border: #24364a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      padding: 14px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }
    h1 {
      margin: 0;
      color: var(--line);
      font-size: 22px;
      letter-spacing: 0;
    }
    .badge {
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 7px 9px;
      color: var(--muted);
      font: 700 12px Consolas, monospace;
      white-space: nowrap;
    }
    .notice {
      border: 1px solid var(--border);
      background: #13263a;
      border-radius: 6px;
      padding: 9px;
      color: var(--yellow);
      font-size: 13px;
      line-height: 1.35;
      margin-bottom: 10px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      min-width: 0;
    }
    .wide { grid-column: 1 / -1; }
    .label {
      color: var(--muted);
      font: 700 11px Consolas, monospace;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    .value {
      font-size: 24px;
      font-weight: 800;
      line-height: 1.05;
      overflow-wrap: anywhere;
    }
    .value.big { font-size: 36px; }
    .signal { color: var(--yellow); }
    .signal.up { color: var(--green); }
    .signal.down { color: var(--red); }
    .status-good { color: var(--green); }
    .status-warn { color: var(--yellow); }
    .status-bad { color: var(--red); }
    canvas {
      display: block;
      width: 100%;
      height: 180px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }
    button, a.button {
      appearance: none;
      border: 1px solid var(--border);
      background: #13263a;
      color: var(--text);
      border-radius: 8px;
      min-height: 46px;
      padding: 10px;
      font-size: 15px;
      font-weight: 800;
      text-align: center;
      text-decoration: none;
    }
    button:active, a.button:active { background: #1d3a58; }
    .signals {
      display: grid;
      gap: 7px;
    }
    .signal-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px;
      font-size: 13px;
    }
    .result {
      font: 800 12px Consolas, monospace;
      padding: 4px 7px;
      border-radius: 5px;
      background: #172638;
      color: var(--muted);
    }
    .result.WIN { color: var(--green); }
    .result.LOSS { color: var(--red); }
    .result.DRAW, .result.PENDING, .result.UNKNOWN { color: var(--yellow); }
    .muted {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .footer {
      margin-top: 10px;
      color: var(--muted);
      font: 700 11px Consolas, monospace;
      text-align: center;
    }
  </style>
</head>
<body>
  <header>
    <h1>PredixAI Trader</h1>
    <div id="readerBadge" class="badge">PARADO</div>
  </header>

  <div class="notice">
    <div>Modo observador. Não é recomendação financeira.</div>
    <div>Modo observador/simulado. Não executa ordens.</div>
  </div>

  <main class="grid">
    <section class="card wide">
      <div class="label">Ativo</div>
      <div id="asset" class="value">-</div>
    </section>

    <section class="card wide">
      <div class="label">Último preço válido</div>
      <div id="price" class="value big">-</div>
    </section>

    <section class="card wide">
      <div class="label">Sinal simulado</div>
      <div id="signal" class="value signal">AGUARDAR</div>
    </section>

    <section class="card">
      <div class="label">Confiança</div>
      <div id="confidence" class="value">-</div>
    </section>

    <section class="card">
      <div class="label">Última leitura</div>
      <div id="age" class="value">-</div>
    </section>

    <section class="card wide">
      <div class="label">Status</div>
      <div id="status" class="value">Parado</div>
      <div id="message" class="muted">Aguardando estado local.</div>
    </section>

    <section class="wide">
      <canvas id="chart" width="680" height="260"></canvas>
    </section>

    <section class="card wide">
      <div class="label">Últimos sinais simulados</div>
      <div id="signals" class="signals">
        <div class="muted">Sem sinais simulados registrados.</div>
      </div>
    </section>
  </main>

  <section class="controls">
    <button type="button" onclick="refreshState()">Atualizar</button>
    <button type="button" onclick="startReader(1)">Iniciar 1s</button>
    <button type="button" onclick="stopReader()">Parar leitor</button>
    <a id="dashboardLink" class="button" href="/mobile">Dashboard</a>
  </section>

  <div id="localUrl" class="footer">Carregando URL local...</div>

  <script>
    const nf = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const chart = document.getElementById("chart");
    const ctx = chart.getContext("2d");

    function fmtPrice(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return nf.format(Number(value));
    }

    function fmtAge(seconds) {
      if (seconds === null || seconds === undefined) return "-";
      if (seconds < 60) return `${seconds}s`;
      return `${Math.floor(seconds / 60)}min`;
    }

    function fmtConfidence(value) {
      if (value === null || value === undefined) return "-";
      let number = Number(value);
      if (Number.isNaN(number)) return "-";
      if (number <= 1) number *= 100;
      return `${Math.round(number)}%`;
    }

    function drawChart(points) {
      const w = chart.width;
      const h = chart.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0b1622";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#1d2f40";
      ctx.lineWidth = 1;
      for (const ratio of [0.25, 0.5, 0.75]) {
        const y = h * ratio;
        ctx.beginPath();
        ctx.moveTo(10, y);
        ctx.lineTo(w - 10, y);
        ctx.stroke();
      }
      if (!points || points.length < 2) {
        ctx.fillStyle = "#a8b5c6";
        ctx.font = "700 22px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Coletando dados para gráfico...", w / 2, h / 2);
        return;
      }
      const values = points.map(p => Number(p.price_value)).filter(v => !Number.isNaN(v));
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = Math.max(1, max - min);
      const pad = 18;
      const step = (w - pad * 2) / Math.max(1, values.length - 1);
      const up = values[values.length - 1] >= values[0];
      ctx.strokeStyle = up ? "#38d66b" : "#ff4d6d";
      ctx.lineWidth = 4;
      ctx.beginPath();
      values.forEach((value, index) => {
        const x = pad + index * step;
        const y = pad + ((max - value) / span) * (h - pad * 2 - 24);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = "#f5f7fb";
      ctx.font = "700 20px Consolas";
      ctx.textAlign = "right";
      ctx.fillText(fmtPrice(values[values.length - 1]), w - pad, h - 12);
    }

    function paintSignals(signals) {
      const box = document.getElementById("signals");
      if (!signals || signals.length === 0) {
        box.innerHTML = '<div class="muted">Sem sinais simulados registrados.</div>';
        return;
      }
      box.innerHTML = signals.map(item => {
        const result = item.result || item.status || "UNKNOWN";
        const price = fmtPrice(item.price);
        const delta = item.delta === null || item.delta === undefined ? "-" : Number(item.delta).toFixed(5);
        return `<div class="signal-row">
          <div>
            <strong>${item.signal || "-"}</strong>
            <div class="muted">${item.asset || "-"} / ${price} / conf. ${fmtConfidence(item.confidence)}</div>
            <div class="muted">delta: ${delta}</div>
          </div>
          <div class="result ${result}">${result}</div>
        </div>`;
      }).join("");
    }

    function paint(data) {
      const state = data.state || {};
      const status = state.status || "Parado";
      const signal = state.signal || "AGUARDAR";
      document.getElementById("asset").textContent = state.asset || "-";
      document.getElementById("price").textContent = fmtPrice(state.price);
      document.getElementById("confidence").textContent = fmtConfidence(state.confidence);
      document.getElementById("age").textContent = fmtAge(state.last_reading_age_seconds);
      document.getElementById("status").textContent = status;
      document.getElementById("message").textContent = state.message || "";
      const signalEl = document.getElementById("signal");
      signalEl.textContent = signal;
      signalEl.className = "value signal";
      if (signal.includes("ALTA")) signalEl.classList.add("up");
      if (signal.includes("BAIXA")) signalEl.classList.add("down");
      const statusEl = document.getElementById("status");
      statusEl.className = "value";
      if (status === "Rodando") statusEl.classList.add("status-good");
      else if (status === "Janela errada" || status === "Bloqueado") statusEl.classList.add("status-bad");
      else statusEl.classList.add("status-warn");
      const badge = document.getElementById("readerBadge");
      badge.textContent = data.reader_running ? "RODANDO" : "PARADO";
      badge.style.color = data.reader_running ? "#38d66b" : "#a8b5c6";
      drawChart(data.history || []);
      paintSignals(data.signals || []);
      document.getElementById("localUrl").textContent = data.mobile_url || window.location.href;
      document.getElementById("dashboardLink").href = `${window.location.protocol}//${window.location.hostname}:8765/`;
    }

    async function refreshState() {
      const response = await fetch("/api/mobile/state", { cache: "no-store" });
      paint(await response.json());
    }

    async function startReader(interval) {
      await fetch(`/api/mobile/start?interval=${interval}`, { method: "POST" });
      await refreshState();
    }

    async function stopReader() {
      await fetch("/api/mobile/stop", { method: "POST" });
      await refreshState();
    }

    refreshState();
    setInterval(refreshState, 1000);
  </script>
</body>
</html>
"""


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return default


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text.upper() in {"UNKNOWN", "NONE", "N/A", "-"}:
        return None

    match = re.search(r"-?\d+(?:[.,]\d+)?", text)
    if not match:
        return None

    number = match.group(0)
    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        number = number.replace(",", ".")

    try:
        return float(number)
    except ValueError:
        return None


def _is_valid_price(value: float | None, asset: str | None = None) -> bool:
    if value is None or value <= 0:
        return False
    if value < 1000:
        return False
    if int(round(value)) in {1, 3, 24, 25, 52, 85, 2026}:
        return False
    asset_text = (asset or "").lower()
    if ("cafe" in asset_text or "asia composite" in asset_text) and 1900 <= value <= 2100:
        return False
    return True


def _format_price_value(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat()


def _file_age_seconds(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(max(0, time.time() - path.stat().st_mtime))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _collect_texts(data: Any) -> list[str]:
    texts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            texts.append(node)

    walk(data)
    return texts


def _asset_from_text(data: Any) -> str:
    text = " ".join(_collect_texts(data))
    if re.search(r"cafe[ií]na\s+index", text, flags=re.IGNORECASE):
        return "Cafeina Index"
    if re.search(r"asia\s+composite\s+index", text, flags=re.IGNORECASE):
        return "Asia Composite Index"
    if re.search(r"latam\s+index", text, flags=re.IGNORECASE):
        return "LATAM Index"
    return ""


def _extract_value(data: Any, keys: set[str]) -> Any:
    normalized = {key.lower() for key in keys}
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in normalized:
                return value
        for value in data.values():
            found = _extract_value(value, keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in reversed(data):
            found = _extract_value(item, keys)
            if found is not None:
                return found
    return None


def _collect_history() -> list[dict[str, Any]]:
    raw_history = _read_json(PRICE_HISTORY_PATH, [])
    if not isinstance(raw_history, list):
        raw_history = []

    points: list[dict[str, Any]] = []
    for index, item in enumerate(raw_history[-3000:], start=1):
        if not isinstance(item, dict):
            continue
        asset = _as_text(item.get("asset")) or _asset_from_text(item)
        price = _parse_float(item.get("price_value"))
        if price is None:
            price = _parse_float(item.get("price"))
        if not _is_valid_price(price, asset):
            continue
        points.append(
            {
                "index": index,
                "timestamp": item.get("timestamp"),
                "asset": asset or "UNKNOWN",
                "price": _format_price_value(price),
                "price_value": _format_price_value(price),
                "confidence": _parse_float(item.get("confidence")),
                "status": item.get("status"),
            }
        )
    return points[-HISTORY_LIMIT:]


def _compute_signal(history: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [
        float(point["price_value"])
        for point in history
        if isinstance(point.get("price_value"), (int, float))
    ]
    if len(prices) < 6:
        return {
            "signal": "AGUARDAR",
            "direction": "COLETANDO",
            "confidence": 20,
            "reason": "Histórico ainda pequeno.",
        }

    delta = prices[-1] - prices[-6]
    short_delta = prices[-1] - prices[-2]
    if abs(delta) < 0.35:
        return {
            "signal": "AGUARDAR",
            "direction": "LATERAL",
            "confidence": 35,
            "reason": "Movimento fraco no histórico recente.",
        }
    if delta > 0:
        return {
            "signal": "OBSERVAR ALTA",
            "direction": "ALTA",
            "confidence": 55 if short_delta >= 0 else 45,
            "reason": "Preço recente acima da base anterior.",
        }
    return {
        "signal": "OBSERVAR BAIXA",
        "direction": "BAIXA",
        "confidence": 55 if short_delta <= 0 else 45,
        "reason": "Preço recente abaixo da base anterior.",
    }


def _normalize_signal(value: Any) -> str:
    text = _as_text(value).upper() or "AGUARDAR"
    replacements = {
        "WAIT": "AGUARDAR",
        "HOLD": "AGUARDAR",
        "CALL": "OBSERVAR ALTA",
        "PUT": "OBSERVAR BAIXA",
        "BUY": "OBSERVAR ALTA",
        "SELL": "OBSERVAR BAIXA",
        "UP": "OBSERVAR ALTA",
        "DOWN": "OBSERVAR BAIXA",
    }
    return replacements.get(text, text)


def _ensure_signal_db() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                asset TEXT,
                price REAL,
                signal TEXT,
                direction TEXT,
                confidence REAL,
                expiration_seconds INTEGER,
                reason TEXT,
                source TEXT,
                status TEXT,
                result_checked_at TEXT,
                result_price REAL,
                result TEXT,
                delta REAL,
                metadata_json TEXT
            )
            """
        )
        conn.commit()


def _history_price_after(
    history: list[dict[str, Any]],
    target_dt: datetime,
) -> float | None:
    for point in history:
        point_dt = _parse_dt(point.get("timestamp"))
        if point_dt is None:
            continue
        if point_dt >= target_dt:
            return _parse_float(point.get("price_value"))
    return None


def _check_pending_signals(history: list[dict[str, Any]]) -> None:
    _ensure_signal_db()
    now = _now()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM signals WHERE status = 'PENDING' ORDER BY id ASC"
        ).fetchall()
        for row in rows:
            created_at = _parse_dt(row["created_at"])
            if created_at is None:
                continue
            expiration_seconds = int(row["expiration_seconds"] or DEFAULT_EXPIRATION_SECONDS)
            target_dt = created_at + timedelta(seconds=expiration_seconds)
            if now < target_dt:
                continue

            entry_price = _parse_float(row["price"])
            result_price = _history_price_after(history, target_dt)
            if result_price is None or entry_price is None:
                result = "UNKNOWN"
                delta = None
            else:
                delta = result_price - entry_price
                if abs(delta) < 0.000001:
                    result = "DRAW"
                elif row["direction"] == "ALTA":
                    result = "WIN" if delta > 0 else "LOSS"
                elif row["direction"] == "BAIXA":
                    result = "WIN" if delta < 0 else "LOSS"
                else:
                    result = "UNKNOWN"

            conn.execute(
                """
                UPDATE signals
                SET status = ?,
                    result = ?,
                    result_checked_at = ?,
                    result_price = ?,
                    delta = ?
                WHERE id = ?
                """,
                (
                    result,
                    result,
                    _now_iso(),
                    result_price,
                    delta,
                    row["id"],
                ),
            )
        conn.commit()


def _register_signal_if_needed(state: dict[str, Any]) -> None:
    signal = str(state.get("signal") or "")
    if signal not in {"OBSERVAR ALTA", "OBSERVAR BAIXA"}:
        return

    asset = str(state.get("asset") or "UNKNOWN")
    direction = "ALTA" if "ALTA" in signal else "BAIXA"
    price = _parse_float(state.get("price"))
    if not _is_valid_price(price, asset):
        return

    _ensure_signal_db()
    now = _now()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT created_at
            FROM signals
            WHERE asset = ? AND direction = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (asset, direction),
        ).fetchone()
        if row:
            last_created = _parse_dt(row["created_at"])
            if last_created is not None:
                elapsed = (now - last_created).total_seconds()
                if elapsed < SIGNAL_COOLDOWN_SECONDS:
                    return

        metadata = {
            "observer_only": True,
            "financial_advice": False,
            "orders_enabled": False,
            "history_count": state.get("valid_readings", 0),
        }
        conn.execute(
            """
            INSERT INTO signals (
                created_at, asset, price, signal, direction, confidence,
                expiration_seconds, reason, source, status, result,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING', ?)
            """,
            (
                _now_iso(),
                asset,
                price,
                signal,
                direction,
                _parse_float(state.get("confidence")),
                DEFAULT_EXPIRATION_SECONDS,
                state.get("reason"),
                "mobile_server",
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        conn.commit()


def _list_signals() -> list[dict[str, Any]]:
    _ensure_signal_db()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, created_at, asset, price, signal, direction, confidence,
                   expiration_seconds, reason, status, result_checked_at,
                   result_price, result, delta
            FROM signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (SIGNALS_LIMIT,),
        ).fetchall()
        return [dict(row) for row in rows]


def _reader_running() -> bool:
    return _reader_process is not None and _reader_process.poll() is None


def _start_reader(interval: int) -> dict[str, Any]:
    global _reader_interval, _reader_process

    interval = max(1, min(10, int(interval)))
    if _reader_running():
        return {
            "status": "ALREADY_RUNNING",
            "interval": _reader_interval,
            "pid": _reader_process.pid if _reader_process else None,
        }

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable,
        "-m",
        "predixai.main",
        "--live-loop",
        "--loop-count",
        "9999",
        "--loop-interval",
        str(interval),
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
    _reader_interval = interval
    return {
        "status": "STARTED",
        "interval": interval,
        "pid": _reader_process.pid,
        "observer_only": True,
    }


def _stop_reader() -> dict[str, Any]:
    global _reader_interval, _reader_process

    if not _reader_running():
        _reader_process = None
        _reader_interval = None
        return {"status": "NOT_RUNNING"}

    pid = _reader_process.pid
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        _reader_process.terminate()
    _reader_process = None
    _reader_interval = None
    return {"status": "STOPPED", "pid": pid}


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def _build_state(
    host_for_url: str | None = None,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    last = _read_json(LAST_READING_PATH, {})
    if not isinstance(last, dict):
        last = {}
    history = _collect_history()
    rejected = _read_json(REJECTED_READINGS_PATH, [])
    if not isinstance(rejected, list):
        rejected = []

    _check_pending_signals(history)

    latest_history = history[-1] if history else {}
    asset = (
        _as_text(_extract_value(last, {"asset", "symbol", "active", "instrument"}))
        or _as_text(latest_history.get("asset"))
        or _asset_from_text(last)
        or "UNKNOWN"
    )
    price = _parse_float(_extract_value(last, {"price_value", "price", "current_price", "last_price"}))
    if not _is_valid_price(price, asset):
        price = _parse_float(latest_history.get("price_value"))
    if not _is_valid_price(price, asset):
        price = None

    computed = _compute_signal(history)
    raw_signal = _extract_value(
        last,
        {"signal", "instruction", "robot_instruction", "decision", "action"},
    )
    signal = _normalize_signal(raw_signal) if raw_signal else computed["signal"]
    if signal not in {"AGUARDAR", "OBSERVAR ALTA", "OBSERVAR BAIXA"}:
        signal = computed["signal"]

    direction = _as_text(_extract_value(last, {"direction", "trend", "market_direction"}))
    if not direction:
        direction = computed["direction"]

    confidence = _parse_float(_extract_value(last, {"confidence", "confidence_pct", "score"}))
    if confidence is None:
        confidence = _parse_float(computed["confidence"])

    reason = (
        _as_text(_extract_value(last, {"reason", "message", "analysis_reason", "explanation"}))
        or computed["reason"]
    )

    last_status = _as_text(last.get("status")).upper()
    ignored_window = last_status == "IGNORED_WINDOW" or bool(last.get("capture_skipped"))
    valid_age = _file_age_seconds(PRICE_HISTORY_PATH) if history else None
    event_age = _file_age_seconds(LAST_READING_PATH)
    age = valid_age if valid_age is not None else event_age

    running = _reader_running()
    if ignored_window:
        status = "Janela errada"
        message = reason or "Janela errada detectada. Clique na corretora no PC."
        signal = "AGUARDAR"
        confidence = 0
    elif running and (valid_age is None or valid_age > max(4, (_reader_interval or 1) * 3)):
        status = "Sem nova leitura"
        message = "Leitor rodando, mas sem nova leitura válida."
    elif running:
        status = "Rodando"
        message = "Leitor ativo. Acompanhe apenas em modo simulado."
    elif valid_age is not None and valid_age <= 3:
        status = "Rodando"
        message = "Leitura recente detectada no runtime local."
    else:
        status = "Parado"
        message = "Inicie o leitor e mantenha a corretora visível no PC."

    if price is None:
        signal = "AGUARDAR"

    state = {
        "asset": asset if asset != "UNKNOWN" else "-",
        "price": _format_price_value(price),
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "status": status,
        "message": message,
        "reason": reason,
        "valid_readings": len(history),
        "last_reading_age_seconds": age,
        "last_runtime_status": last_status or "NO_DATA",
        "last_window_title": last.get("window_title") or (last.get("broker_window") or {}).get("title"),
    }

    _register_signal_if_needed(state)
    signals = _list_signals()

    host = host_for_url or _local_ip()
    return {
        "notice": OBSERVATION_NOTICE,
        "simulation_notice": SIMULATION_NOTICE,
        "reader_running": running,
        "reader_interval": _reader_interval,
        "mobile_url": f"http://{host}:{port}/mobile",
        "state": state,
        "history": history,
        "signals": signals,
        "recent_rejections": rejected[-10:],
        "db_path": str(SIGNALS_DB_PATH),
        "runtime": {
            "last_live_reading": str(LAST_READING_PATH),
            "live_price_history": str(PRICE_HISTORY_PATH),
            "rejected_live_readings": str(REJECTED_READINGS_PATH),
        },
    }


def _host_from_header(host_header: str | None) -> str:
    host = (host_header or "").split(":", 1)[0]
    if host in {"", "0.0.0.0", "127.0.0.1", "localhost"}:
        return _local_ip()
    return host


def _port_from_header(host_header: str | None, default: int = DEFAULT_PORT) -> int:
    if not host_header or ":" not in host_header:
        return default
    try:
        return int(host_header.rsplit(":", 1)[1])
    except ValueError:
        return default


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _handle_get(path: str, host_header: str | None = None) -> tuple[int, str, bytes]:
    if path in {"/", "/mobile"}:
        return 200, "text/html; charset=utf-8", MOBILE_HTML.encode("utf-8")
    if path == "/api/mobile/state":
        host = _host_from_header(host_header)
        port = _port_from_header(host_header)
        return 200, "application/json; charset=utf-8", _json_bytes(
            _build_state(host_for_url=host, port=port)
        )
    return 404, "application/json; charset=utf-8", _json_bytes({"status": "NOT_FOUND"})


def _handle_post(
    path: str,
    query: dict[str, list[str]] | None = None,
) -> tuple[int, str, bytes]:
    query = query or {}
    if path == "/api/mobile/start":
        interval = int((query.get("interval") or ["1"])[0])
        return 200, "application/json; charset=utf-8", _json_bytes(_start_reader(interval))
    if path == "/api/mobile/stop":
        return 200, "application/json; charset=utf-8", _json_bytes(_stop_reader())
    return 404, "application/json; charset=utf-8", _json_bytes({"status": "NOT_FOUND"})


class MobileRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        status, content_type, body = _handle_get(
            parsed.path,
            host_header=self.headers.get("Host"),
        )
        self._send(status, content_type, body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        status, content_type, body = _handle_post(
            parsed.path,
            query=parse_qs(parsed.query),
        )
        self._send(status, content_type, body)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(body)


def create_mobile_app() -> Flask:
    if not HAS_FLASK:
        raise RuntimeError("Flask nao esta disponivel; usando servidor http.server.")

    app = Flask(__name__)

    @app.after_request
    def add_no_cache_headers(response):  # type: ignore[no-untyped-def]
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    @app.route("/")
    def root():  # type: ignore[no-untyped-def]
        return MOBILE_HTML

    @app.route("/mobile")
    def mobile():  # type: ignore[no-untyped-def]
        return MOBILE_HTML

    @app.route("/api/mobile/state")
    def mobile_state():  # type: ignore[no-untyped-def]
        host = _host_from_header(request.host)
        port = _port_from_header(request.host)
        return jsonify(_build_state(host_for_url=host, port=port))

    @app.route("/api/mobile/start", methods=["POST"])
    def mobile_start():  # type: ignore[no-untyped-def]
        interval = request.args.get("interval", "1")
        return jsonify(_start_reader(int(interval)))

    @app.route("/api/mobile/stop", methods=["POST"])
    def mobile_stop():  # type: ignore[no-untyped-def]
        return jsonify(_stop_reader())

    return app


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    _ensure_signal_db()
    local_ip = _local_ip()
    print("PredixAI Trader Mobile Server")
    print(OBSERVATION_NOTICE)
    print(SIMULATION_NOTICE)
    print(f"Local PC: http://127.0.0.1:{port}/mobile")
    print(f"Celular na mesma Wi-Fi: http://{local_ip}:{port}/mobile")
    print("Endpoints: GET /api/mobile/state | POST /api/mobile/start?interval=1 | POST /api/mobile/stop")
    if HAS_FLASK:
        create_mobile_app().run(host=host, port=port, debug=False, use_reloader=False)
        return

    print("Flask nao encontrado; usando http.server local da biblioteca padrao.")
    server = ThreadingHTTPServer((host, port), MobileRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Servidor mobile interrompido.")
    finally:
        server.server_close()


def smoke_test(port: int = DEFAULT_PORT) -> int:
    _ensure_signal_db()
    if HAS_FLASK:
        app = create_mobile_app()
        with app.test_client() as client:
            mobile_response = client.get("/mobile")
            state_response = client.get("/api/mobile/state")
            print(f"SMOKE_MOBILE_STATUS={mobile_response.status_code}")
            print(f"SMOKE_STATE_STATUS={state_response.status_code}")
            payload = state_response.get_json(silent=True) or {}
            print(f"SMOKE_HAS_STATE={'state' in payload}")
            print(f"SMOKE_MOBILE_URL=http://{_local_ip()}:{port}/mobile")
        return 0 if mobile_response.status_code == 200 and state_response.status_code == 200 else 1

    mobile_status, _, _ = _handle_get("/mobile")
    state_status, _, state_body = _handle_get(
        "/api/mobile/state",
        host_header=f"127.0.0.1:{port}",
    )
    payload = json.loads(state_body.decode("utf-8"))
    print(f"SMOKE_MOBILE_STATUS={mobile_status}")
    print(f"SMOKE_STATE_STATUS={state_status}")
    print(f"SMOKE_HAS_STATE={'state' in payload}")
    print(f"SMOKE_MOBILE_URL=http://{_local_ip()}:{port}/mobile")
    return 0 if mobile_status == 200 and state_status == 200 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="predixai_trader_mobile_server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.smoke_test:
        return smoke_test(port=args.port)
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
