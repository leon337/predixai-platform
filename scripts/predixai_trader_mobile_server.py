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
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
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
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from predixai.mobile.signal_screen import build_mobile_signal_screen
from predixai.trader.confluence_engine import ConfluenceEngine
from predixai.trader.mobile_session_contract import (
    build_mobile_session_contract,
    validate_mobile_session_contract,
)
from predixai.trader.paper_trade import build_paper_trade_from_mobile_signal
from predixai.trader.strategy_engine import MinimalStrategyEngine, StrategyInput

RUNTIME_DIR = ROOT_DIR / "data" / "runtime"
LAST_READING_PATH = RUNTIME_DIR / "last_live_reading.json"
PRICE_HISTORY_PATH = RUNTIME_DIR / "live_price_history.json"
REJECTED_READINGS_PATH = RUNTIME_DIR / "rejected_live_readings.json"
SIGNALS_DB_PATH = RUNTIME_DIR / "predixai_trader_signals.db"
MOBILE_SESSION_PATH = RUNTIME_DIR / "mobile_current_session.json"
MOBILE_BACKUPS_DIR = RUNTIME_DIR / "backups"

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
HISTORY_LIMIT = 60
SESSION_HISTORY_LIMIT = 100
SIGNALS_LIMIT = 20
SIGNAL_COOLDOWN_SECONDS = 3
DEFAULT_EXPIRATION_SECONDS = 30
DEFAULT_READER_INTERVAL_SECONDS = 3
SIGNAL_ANALYSIS_INTERVAL_SECONDS = 3
ALLOWED_EXPIRATION_SECONDS = {30}
RESULT_PRICE_TOLERANCE_SECONDS = 10
UNKNOWN_AFTER_EXPIRATION_SECONDS = 45
WAITING_RESULT_STATUS = "WAITING_RESULT"
UNKNOWN_NO_HISTORY_REASON = "Sem preço válido entre 30s e 40s após o sinal"
SIMULATED_BRIDGE_SOURCE = "MOBILE_FIRST_SIMULATED_BRIDGE"
SIMULATED_START_ROUTES = {"/mobile/session/start", "/api/mobile/simulated-session/start"}
DEFAULT_SIMULATED_ASSET = "Cafeina Index"
ALLOWED_SIMULATED_STRATEGIES = {
    "LEGACY_MOMENTUM",
    "SUPPORT_RESISTANCE",
    "PRICE_ACTION",
    "CANDLE_REVERSAL",
}
ALLOWED_SIMULATED_RISK_PROFILES = {"CONSERVATIVE", "MODERATE", "AGGRESSIVE"}

OBSERVATION_NOTICE = "Modo observador. Não é recomendação financeira."
SIMULATION_NOTICE = "Modo observador/simulado. Não executa ordens."

_reader_process: subprocess.Popen | None = None
_reader_interval: int | None = None
_reader_process_cache_at: float = 0.0
_reader_process_cache: list[dict[str, Any]] = []
_reader_start_lock = threading.Lock()


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
    .expiration-controls {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;
      margin-bottom: 8px;
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
    .admin-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
      flex-wrap: wrap;
    }
    .admin-actions button {
      min-height: 34px;
      padding: 7px 10px;
      font-size: 12px;
    }
    .admin-message {
      color: var(--muted);
      font-size: 12px;
    }
    .expiration-controls button {
      min-height: 40px;
      padding: 8px;
      font-size: 14px;
    }
    .expiration-controls button.active {
      border-color: var(--line);
      color: var(--line);
      background: #0b2636;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 7px;
      margin-bottom: 8px;
    }
    .metric {
      min-width: 0;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 6px;
      text-align: center;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font: 700 10px Consolas, monospace;
      margin-bottom: 3px;
    }
    .metric strong {
      display: block;
      font-size: 18px;
      overflow-wrap: anywhere;
    }
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
    .result.DRAW, .result.PENDING, .result.WAITING_RESULT, .result.UNKNOWN { color: var(--yellow); }
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
    .chart-note {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
  
/* PTP113B31B2_OBSERVADOR_CONTRACT_UX */
.ux-contract-card,
.ux-live-chart-card {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel-2);
  padding: 10px;
  margin: 8px 0;
}
.ux-contract-title {
  color: var(--line);
  font: 800 12px Consolas, monospace;
  text-transform: uppercase;
  letter-spacing: .04em;
  margin-bottom: 8px;
}
.ux-contract-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.ux-contract-item {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
  background: #081421;
}
.ux-contract-label {
  color: var(--muted);
  font: 700 10px Consolas, monospace;
  text-transform: uppercase;
}
.ux-contract-value {
  margin-top: 4px;
  color: var(--text);
  font-size: 18px;
  font-weight: 800;
}
.ux-security-line {
  margin-top: 8px;
  color: var(--yellow);
  font: 700 11px Consolas, monospace;
}
.ux-chart-canvas {
  width: 100%;
  height: 140px;
  display: block;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #07111b;
}
.ux-chart-status {
  margin-top: 6px;
  color: var(--muted);
  font: 700 11px Consolas, monospace;
}
.ux-processing {
  outline: 2px solid var(--yellow) !important;
  box-shadow: 0 0 14px rgba(255, 191, 0, .35) !important;
}
.ux-ok {
  outline: 2px solid var(--green) !important;
  box-shadow: 0 0 14px rgba(56, 214, 107, .35) !important;
}
.ux-error {
  outline: 2px solid var(--red) !important;
  box-shadow: 0 0 14px rgba(255, 77, 109, .35) !important;
}
.ux-toast {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 9999;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #061018;
  color: var(--text);
  padding: 10px;
  font: 800 13px Arial, sans-serif;
  box-shadow: 0 8px 28px rgba(0,0,0,.35);
}
@media (max-width: 640px) {
  .ux-contract-grid {
    grid-template-columns: 1fr;
  }
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

    <section class="card">
      <div class="label">Suporte</div>
      <div id="support" class="value">-</div>
    </section>

    <section class="card">
      <div class="label">Resistência</div>
      <div id="resistance" class="value">-</div>
    </section>

    <section class="card wide">
      <div class="label">Sinal simulado</div>
      <div id="signal" class="value signal">AGUARDAR</div>
    </section>

    <section class="card wide">
      <div class="label">Expiração simulada</div>
      <div id="readInterval" class="muted">Leitura de preço: 3s</div>
      <div id="signalInterval" class="muted">Análise de sinal: 3s</div>
      <div id="expirationCurrent" class="muted">Expiração: 30s</div>
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

    <section class="card wide">
      <div class="label">Diagnóstico do preço</div>
      <div class="metrics">
        <div class="metric"><span>Idade</span><strong id="diagPriceAge">-</strong></div>
        <div class="metric"><span>Histórico</span><strong id="diagHistoryCount">0</strong></div>
        <div class="metric"><span>Média</span><strong id="diagAvgInterval">-</strong></div>
        <div class="metric"><span>Aguardando</span><strong id="diagWaiting">0</strong></div>
      </div>
      <div id="diagLastTimestamp" class="muted">Último timestamp: -</div>
      <div id="diagFinalSearch" class="muted">Busca do preço final: -</div>
      <div id="diagTickCount" class="muted">price_ticks SQLite: -</div>
      <div class="admin-actions">
        <button type="button" onclick="resetSession()">Limpar sessão</button>
        <span id="resetMessage" class="admin-message"></span>
      </div>
    </section>

    <section class="card wide">
      <div class="label">Auditoria simulada</div>
      <div class="metrics">
        <div class="metric"><span>Total</span><strong id="statsTotal">0</strong></div>
        <div class="metric"><span>Fechados</span><strong id="statsClosed">0</strong></div>
        <div class="metric"><span>Pendentes</span><strong id="statsPending">0</strong></div>
        <div class="metric"><span>WIN</span><strong id="statsWin">0</strong></div>
        <div class="metric"><span>LOSS</span><strong id="statsLoss">0</strong></div>
        <div class="metric"><span>DRAW</span><strong id="statsDraw">0</strong></div>
        <div class="metric"><span>UNKNOWN</span><strong id="statsUnknown">0</strong></div>
        <div class="metric"><span>Taxa</span><strong id="statsHitRate">0%</strong></div>
      </div>
      <div id="latestSignal" class="muted">Último sinal: -</div>
      <div id="latestRemaining" class="muted">Tempo restante: -</div>
      <div id="latestResult" class="muted">Resultado: -</div>
    </section>

    <section class="wide">
      <canvas id="chart" width="680" height="260"></canvas>
      <div id="chartLegend" class="chart-note">Suporte: - / Resistência: - / Último sinal: -</div>
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
    <button type="button" onclick="startSimulatedSession()">Iniciar simulado</button>
    <button type="button" onclick="stopReader()">Parar leitor</button>
    <a id="dashboardLink" class="button" href="/mobile">Dashboard</a>
  </section>

  <div id="localUrl" class="footer">Carregando URL local...</div>

  <script>
    const nf = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const chart = document.getElementById("chart");
    const ctx = chart.getContext("2d");
    let expirationSeconds = 30;
    let expirationLabel = "30s";

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

    function fmtRemaining(seconds) {
      if (seconds === null || seconds === undefined) return "-";
      const value = Math.max(0, Number(seconds) || 0);
      if (value < 60) return `${Math.ceil(value)}s`;
      return `${Math.floor(value / 60)}min ${Math.ceil(value % 60)}s`;
    }

    function fmtHitRate(value) {
      const number = Number(value || 0);
      return `${number.toFixed(1)}%`;
    }

    function fmtDateTime(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "-";
      return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function updateExpirationControls() {
      document.querySelectorAll("[data-expiration-label]").forEach(button => {
        const active = button.dataset.expirationLabel === expirationLabel;
        button.classList.toggle("active", active);
      });
      document.getElementById("expirationCurrent").textContent = "Expiração: 30s";
    }

    function setExpiration(seconds, label) {
      expirationSeconds = 30;
      expirationLabel = "30s";
      updateExpirationControls();
      refreshState();
    }

    function drawChart(points, support, resistance, signals) {
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
      const signalValues = (signals || []).map(s => Number(s.entry_price ?? s.price)).filter(v => !Number.isNaN(v));
      const supportValue = Number(support);
      const resistanceValue = Number(resistance);
      if (!Number.isNaN(supportValue)) values.push(supportValue);
      if (!Number.isNaN(resistanceValue)) values.push(resistanceValue);
      values.push(...signalValues);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = Math.max(0.000001, max - min);
      const pad = 18;
      const priceValues = points.map(p => Number(p.price_value)).filter(v => !Number.isNaN(v));
      const times = points
        .map(p => Date.parse(p.timestamp || p.created_at || ""))
        .filter(v => !Number.isNaN(v));
      const minTime = times.length ? Math.min(...times) : null;
      const maxTime = times.length ? Math.max(...times) : null;
      const timeSpan = minTime !== null && maxTime !== null ? Math.max(1, maxTime - minTime) : 1;
      function yFor(value) {
        return pad + ((max - value) / span) * (h - pad * 2 - 24);
      }
      function xForPoint(index, timestamp) {
        const parsed = Date.parse(timestamp || "");
        if (minTime !== null && maxTime !== null && !Number.isNaN(parsed)) {
          return pad + ((parsed - minTime) / timeSpan) * (w - pad * 2);
        }
        return pad + index * ((w - pad * 2) / Math.max(1, points.length - 1));
      }
      function xForSignal(signal, fallbackIndex) {
        const parsed = Date.parse(signal.emitted_at || signal.created_at || "");
        if (minTime !== null && maxTime !== null && !Number.isNaN(parsed)) {
          const clamped = Math.min(maxTime, Math.max(minTime, parsed));
          return pad + ((clamped - minTime) / timeSpan) * (w - pad * 2);
        }
        return w - pad - fallbackIndex * 12;
      }
      function drawLevel(value, color, label) {
        if (Number.isNaN(value)) return;
        const y = yFor(value);
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.setLineDash([7, 5]);
        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(w - pad, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        ctx.font = "700 12px Consolas";
        ctx.textAlign = "left";
        ctx.fillText(`${label} ${fmtPrice(value)}`, pad + 4, Math.max(14, y - 4));
        ctx.restore();
      }
      const up = priceValues[priceValues.length - 1] >= priceValues[0];
      ctx.strokeStyle = up ? "#38d66b" : "#ff4d6d";
      ctx.lineWidth = 4;
      ctx.beginPath();
      priceValues.forEach((value, index) => {
        const x = xForPoint(index, points[index]?.timestamp);
        const y = yFor(value);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      drawLevel(supportValue, "#ffbf00", "S");
      drawLevel(resistanceValue, "#00e5ff", "R");
      (signals || []).slice(0, 8).forEach((signal, index) => {
        const entry = Number(signal.entry_price ?? signal.price);
        if (Number.isNaN(entry)) return;
        const x = xForSignal(signal, index);
        const y = yFor(entry);
        const isUp = String(signal.direction || "").includes("ALTA");
        const result = signal.result || signal.status || "WAITING_RESULT";
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = isUp ? "#38d66b" : "#ff4d6d";
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = result === "WIN" ? "#38d66b" : result === "LOSS" ? "#ff4d6d" : "#ffbf00";
        ctx.stroke();
        ctx.fillStyle = "#f5f7fb";
        ctx.font = "700 10px Consolas";
        ctx.textAlign = "center";
        ctx.fillText(["PENDING", "WAITING_RESULT"].includes(result) ? "..." : result, x, Math.max(12, y - 9));
      });
      ctx.fillStyle = "#f5f7fb";
      ctx.font = "700 20px Consolas";
      ctx.textAlign = "right";
      ctx.fillText(fmtPrice(priceValues[priceValues.length - 1]), w - pad, h - 12);
    }

    function paintSignals(signals) {
      const box = document.getElementById("signals");
      if (!signals || signals.length === 0) {
        box.innerHTML = '<div class="muted">Sem sinais simulados registrados.</div>';
        return;
      }
      box.innerHTML = signals.map(item => {
        const result = item.result || item.status || "UNKNOWN";
        const price = fmtPrice(item.entry_price ?? item.price);
        const resultPrice = fmtPrice(item.result_price);
        const delta = item.delta === null || item.delta === undefined ? "-" : Number(item.delta).toFixed(5);
        const waiting = ["PENDING", "WAITING_RESULT"].includes(item.status || result);
        const remaining = waiting ? `restante: ${fmtRemaining(item.remaining_seconds)}` : `resultado: ${result}`;
        const expiration = item.expiration_seconds || 30;
        const unknownReason = result === "UNKNOWN" ? (item.result_reason || item.unknown_reason || "Sem preço válido entre 30s e 40s após o sinal") : "";
        return `<div class="signal-row">
          <div>
            <strong>${item.signal || "-"} ${item.direction ? `(${item.direction})` : ""}</strong>
            <div class="muted">${item.asset || "-"} / ${price} / conf. ${fmtConfidence(item.confidence)}</div>
            <div class="muted">emitido: ${fmtDateTime(item.emitted_at || item.created_at)} / confirmado: ${fmtDateTime(item.result_checked_at)}</div>
            <div class="muted">preço final: ${resultPrice}</div>
            <div class="muted">exp. ${expiration}s / ${remaining}</div>
            <div class="muted">delta: ${delta}</div>
            ${unknownReason ? `<div class="muted">${unknownReason}</div>` : ""}
          </div>
          <div class="result ${result}">${result}</div>
        </div>`;
      }).join("");
    }

    function paintStats(stats) {
      stats = stats || {};
      const latest = stats.latest_signal || null;
      document.getElementById("statsTotal").textContent = stats.total || 0;
      document.getElementById("statsClosed").textContent = stats.closed || 0;
      document.getElementById("statsPending").textContent = stats.pending || 0;
      document.getElementById("statsWin").textContent = stats.win || 0;
      document.getElementById("statsLoss").textContent = stats.loss || 0;
      document.getElementById("statsDraw").textContent = stats.draw || 0;
      document.getElementById("statsUnknown").textContent = stats.unknown || 0;
      document.getElementById("statsHitRate").textContent = fmtHitRate(stats.hit_rate_percent);
      if (!latest) {
        document.getElementById("latestSignal").textContent = "Último sinal: -";
        document.getElementById("latestRemaining").textContent = "Tempo restante: -";
        document.getElementById("latestResult").textContent = "Resultado: -";
        return;
      }
      document.getElementById("latestSignal").textContent = `Último sinal: ${latest.direction || "-"} / emitido ${fmtDateTime(latest.emitted_at || latest.created_at)} / entrada ${fmtPrice(latest.entry_price ?? latest.price)}`;
      document.getElementById("latestRemaining").textContent = ["PENDING", "WAITING_RESULT"].includes(latest.status)
        ? `Tempo restante: ${fmtRemaining(latest.remaining_seconds)}`
        : `Confirmado: ${fmtDateTime(latest.result_checked_at)} / preço final ${fmtPrice(latest.result_price)}`;
      const latestReason = (latest.result || latest.status) === "UNKNOWN" ? ` / ${latest.result_reason || latest.unknown_reason || "Sem preço válido entre 30s e 40s após o sinal"}` : "";
      document.getElementById("latestResult").textContent = `Resultado: ${latest.result || latest.status || "-"}${latestReason}`;
    }

    function paintDiagnostics(diagnostics) {
      diagnostics = diagnostics || {};
      document.getElementById("diagPriceAge").textContent = fmtAge(diagnostics.last_price_age_seconds);
      document.getElementById("diagHistoryCount").textContent = diagnostics.history_count || 0;
      document.getElementById("diagAvgInterval").textContent =
        diagnostics.average_interval_seconds === null || diagnostics.average_interval_seconds === undefined
          ? "-"
          : `${Number(diagnostics.average_interval_seconds).toFixed(1)}s`;
      document.getElementById("diagWaiting").textContent = diagnostics.waiting_result_count || 0;
      document.getElementById("diagLastTimestamp").textContent = `Último timestamp: ${fmtDateTime(diagnostics.last_history_timestamp)}`;
      document.getElementById("diagFinalSearch").textContent = `Busca do preço final: ${diagnostics.final_price_search_status || "-"}`;
      document.getElementById("diagTickCount").textContent = `price_ticks SQLite: ${diagnostics.price_ticks_count ?? 0}`;
    }

    function paint(data) {
      const state = data.state || {};
      const status = state.status || "Parado";
      const signal = state.signal || "AGUARDAR";
      if ([30, 60].includes(Number(data.expiration_seconds))) {
        expirationSeconds = Number(data.expiration_seconds);
      }
      updateExpirationControls();
      document.getElementById("asset").textContent = state.asset || "-";
      document.getElementById("price").textContent = fmtPrice(state.price);
      document.getElementById("support").textContent = fmtPrice(data.support);
      document.getElementById("resistance").textContent = fmtPrice(data.resistance);
      document.getElementById("readInterval").textContent = `Leitura de preço: ${data.reader_interval || 3}s`;
      document.getElementById("signalInterval").textContent = `Análise de sinal: ${data.signal_analysis_interval || 3}s`;
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
      if (status.startsWith("Rodando")) statusEl.classList.add("status-good");
      else if (status === "Janela errada" || status === "Bloqueado") statusEl.classList.add("status-bad");
      else statusEl.classList.add("status-warn");
      const badge = document.getElementById("readerBadge");
      badge.textContent = data.reader_running ? "RODANDO" : "PARADO";
      badge.style.color = data.reader_running ? "#38d66b" : "#a8b5c6";
      const signals = data.signals || [];
      drawChart(data.price_history || data.history || [], data.support, data.resistance, signals);
      paintSignals(data.signals || []);
      paintStats(data.signal_stats || {});
      paintDiagnostics(data.price_diagnostics || {});
      const latest = (data.signal_stats || {}).latest_signal || signals[0] || null;
      document.getElementById("chartLegend").textContent =
        `Suporte: ${fmtPrice(data.support)} / Resistência: ${fmtPrice(data.resistance)} / preço: ${fmtPrice(state.price)} / hora: ${fmtDateTime((data.price_history || data.history || []).slice(-1)[0]?.timestamp)} / último sinal: ${latest ? `${latest.direction || "-"} ${latest.result || latest.status || "-"}` : "-"}`;
      document.getElementById("localUrl").textContent = data.mobile_url || window.location.href;
      document.getElementById("dashboardLink").href = `${window.location.protocol}//${window.location.hostname}:8765/`;
    }

    async function refreshState() {
      const response = await fetch(`/api/mobile/state?expiration=${expirationSeconds}`, { cache: "no-store" });
      paint(await response.json());
    }

    async function startReader(interval) {
      await startSimulatedSession();
    }

    async function startSimulatedSession() {
      await fetch("/mobile/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session: {
            session_type: "TEST",
            session_name: "PTP-113 simulated mobile-first"
          },
          strategy: {
            primary_strategy: "LEGACY_MOMENTUM",
            strategy_stack: ["LEGACY_MOMENTUM"],
            confluence_required: true,
            min_confidence: 70
          },
          bankroll: {
            simulated: true,
            initial_bankroll: 100,
            current_bankroll: 100,
            initial_entry: 5,
            current_entry: 5
          },
          risk: {
            risk_profile: "CONSERVATIVE",
            stop_loss: 20,
            take_profit: 20,
            max_signals: 10,
            max_losses: 3
          },
          operation: {
            paper_trade_enabled: true,
            payout_min: 80,
            expiration_seconds: 30,
            max_open_trades: 1
          },
          simulated_market: {
            asset: "Cafeina Index",
            previous_price: 4100.00,
            current_price: 4182.10,
            recent_prices: [4100.00, 4120.00, 4140.00, 4160.00, 4175.00, 4182.10]
          }
        })
      });
      await refreshState();
    }

    async function stopReader() {
      await fetch("/api/mobile/stop", { method: "POST" });
      await refreshState();
    }

    async function resetSession() {
      const confirmed = window.confirm("Isso fará backup e limpará apenas os dados da sessão/testes. Deseja continuar?");
      if (!confirmed) return;
      const message = document.getElementById("resetMessage");
      message.textContent = "Criando backup e limpando sessão...";
      const response = await fetch("/api/mobile/reset-session", { method: "POST" });
      const payload = await response.json();
      if (!response.ok || payload.status !== "RESET_OK") {
        message.textContent = payload.message || "Falha ao limpar sessão.";
        return;
      }
      message.textContent = "Sessão limpa criada com backup.";
      await refreshState();
    }

    updateExpirationControls();
    refreshState();
    setInterval(refreshState, 1000);
  </script>

<script>
/* PTP113B31B2_OBSERVADOR_CONTRACT_UX */
(function () {
  const UX_MARKER = "PTP113B31B2_OBSERVADOR_CONTRACT_UX_RUNTIME";

  function $(id) {
    return document.getElementById(id);
  }

  function showToast(message, mode) {
    let toast = $("predixai-ux-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "predixai-ux-toast";
      toast.className = "ux-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = "ux-toast";
    if (mode === "error") toast.classList.add("ux-error");
    if (mode === "ok") toast.classList.add("ux-ok");
    setTimeout(function () {
      if (toast) toast.remove();
    }, 2200);
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "object") {
      if (value.label) return value.label;
      if (value.name) return value.name;
      if (value.key) return value.key;
      try { return JSON.stringify(value); } catch (err) { return "-"; }
    }
    return String(value);
  }

  function asMoney(value) {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "string" && value.indexOf("R$") >= 0) return value;
    let numberValue = value;
    if (typeof numberValue === "string") {
      numberValue = numberValue.replace("R$", "").trim().replaceAll(".", "").replace(",", ".");
    }
    numberValue = Number(numberValue);
    if (!Number.isFinite(numberValue)) return displayValue(value);
    return numberValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function deepPick(obj, names) {
    const wanted = names.map(function (x) { return String(x).toLowerCase(); });
    const stack = [obj];
    const seen = new Set();

    while (stack.length) {
      const current = stack.shift();
      if (!current || typeof current !== "object" || seen.has(current)) continue;
      seen.add(current);

      for (const key of Object.keys(current)) {
        const low = key.toLowerCase();
        if (wanted.indexOf(low) >= 0) return current[key];
      }

      for (const key of Object.keys(current)) {
        const low = key.toLowerCase();
        for (const name of wanted) {
          if (low.indexOf(name) >= 0) return current[key];
        }
      }

      for (const key of Object.keys(current)) {
        const val = current[key];
        if (val && typeof val === "object") stack.push(val);
      }
    }
    return undefined;
  }

  function setText(id, value, formatter) {
    const el = $(id);
    if (!el) return;
    el.textContent = formatter ? formatter(value) : displayValue(value);
  }

  function ensureCards() {
    if (!$("predixai-contract-card")) {
      const card = document.createElement("section");
      card.id = "predixai-contract-card";
      card.className = "ux-contract-card";
      card.innerHTML =
        '<div class="ux-contract-title">Contrato da sessão simulada</div>' +
        '<div class="ux-contract-grid">' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Saldo atual</div><div id="ux-saldo-atual" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Banca inicial</div><div id="ux-banca-inicial" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Entrada atual</div><div id="ux-entrada-atual" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Meta de lucro</div><div id="ux-meta-lucro" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Stop / limite</div><div id="ux-stop-limite" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Recuperação</div><div id="ux-recuperacao" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Próxima entrada</div><div id="ux-proxima-entrada" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Exposição máxima</div><div id="ux-exposicao-maxima" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Modo operacional</div><div id="ux-modo-operacional" class="ux-contract-value">-</div></div>' +
        '<div class="ux-contract-item"><div class="ux-contract-label">Estratégia</div><div id="ux-estrategia" class="ux-contract-value">-</div></div>' +
        '</div>' +
        '<div id="ux-security-line" class="ux-security-line">Segurança simulada: carregando...</div>';

      const anchor = document.querySelector(".notice") || document.querySelector("header") || document.body.firstElementChild;
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(card, anchor.nextSibling);
      } else {
        document.body.insertBefore(card, document.body.firstChild);
      }
    }

    if (!$("predixai-live-chart-card")) {
      const chart = document.createElement("section");
      chart.id = "predixai-live-chart-card";
      chart.className = "ux-live-chart-card";
      chart.innerHTML =
        '<div class="ux-contract-title">Gráfico da sessão</div>' +
        '<canvas id="predixai-ux-price-chart" class="ux-chart-canvas" width="900" height="180"></canvas>' +
        '<div id="predixai-ux-chart-status" class="ux-chart-status">Coletando dados para gráfico...</div>';

      const contract = $("predixai-contract-card");
      if (contract && contract.parentNode) {
        contract.parentNode.insertBefore(chart, contract.nextSibling);
      } else {
        document.body.appendChild(chart);
      }
    }
  }

  function extractPoints(state) {
    const raw = state.price_ticks || state.ticks || state.history || [];
    if (!Array.isArray(raw)) return [];
    return raw.map(function (row) {
      if (typeof row === "number") return row;
      if (!row || typeof row !== "object") return NaN;
      return Number(row.price_value ?? row.price ?? row.value ?? row.close ?? row.last_price);
    }).filter(function (v) {
      return Number.isFinite(v);
    }).slice(-40);
  }

  function drawChart(points) {
    const canvas = $("predixai-ux-price-chart");
    const status = $("predixai-ux-chart-status");
    if (!canvas || !canvas.getContext) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#07111b";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "#203245";
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {
      const y = Math.round((height / 5) * i);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    if (!points || points.length < 2) {
      ctx.fillStyle = "#a8b5c6";
      ctx.font = "bold 20px Arial";
      ctx.textAlign = "center";
      ctx.fillText("Coletando dados para gráfico...", width / 2, height / 2);
      if (status) status.textContent = "Aguardando pelo menos 2 preços para desenhar linha.";
      return;
    }

    const min = Math.min.apply(null, points);
    const max = Math.max.apply(null, points);
    const range = Math.max(max - min, 0.000001);

    ctx.strokeStyle = "#00e5ff";
    ctx.lineWidth = 3;
    ctx.beginPath();

    points.forEach(function (value, index) {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
      const y = height - ((value - min) / range) * (height - 20) - 10;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();

    if (status) {
      const last = points[points.length - 1];
      status.textContent = "Gráfico atualizado: " + new Date().toLocaleTimeString("pt-BR") + " | último preço: " + last.toLocaleString("pt-BR");
    }
  }

  function updateSecurity(state) {
    const line = $("ux-security-line");
    if (!line) return;

    const flags = [
      "simulation_only",
      "orders_enabled",
      "real_money_enabled",
      "auto_click_enabled",
      "broker_login_enabled",
      "credentials_allowed"
    ];

    line.textContent = "Segurança simulada: " + flags.map(function (key) {
      const value = deepPick(state, [key]);
      return key + "=" + displayValue(value);
    }).join(" | ");
  }

  async function updateContract() {
    ensureCards();

    try {
      const response = await fetch("/api/mobile/state?ux_contract=1", { cache: "no-store" });
      const state = await response.json();

      setText("ux-saldo-atual", deepPick(state, ["current_balance", "saldo_atual", "saldo", "balance"]), asMoney);
      setText("ux-banca-inicial", deepPick(state, ["initial_bankroll", "starting_balance", "banca_inicial", "banca", "bankroll"]), asMoney);
      setText("ux-entrada-atual", deepPick(state, ["current_entry", "entry_value", "entry_amount", "stake", "entrada_atual", "entrada", "entry"]), asMoney);
      setText("ux-meta-lucro", deepPick(state, ["profit_target", "target_profit", "meta_lucro", "meta"]), asMoney);
      setText("ux-stop-limite", deepPick(state, ["stop_loss", "loss_limit", "max_loss", "limite", "limit", "stop"]), asMoney);
      setText("ux-recuperacao", deepPick(state, ["recovery_mode", "recovery_strategy", "selected_recovery", "recuperacao", "recovery", "martingale", "soros", "smartgale"]));
      setText("ux-proxima-entrada", deepPick(state, ["next_entry", "next_stake", "proxima_entrada", "próxima_entrada"]), asMoney);
      setText("ux-exposicao-maxima", deepPick(state, ["max_exposure", "exposicao_maxima", "exposição_maxima", "exposure", "entrada_maxima", "entrada máxima"]), asMoney);
      setText("ux-modo-operacional", deepPick(state, ["operational_mode", "modo_operacional", "mode"]));
      setText("ux-estrategia", deepPick(state, ["strategy", "selected_strategy", "estrategia"]));

      updateSecurity(state);
      drawChart(extractPoints(state));
    } catch (err) {
      const status = $("predixai-ux-chart-status");
      if (status) status.textContent = "Erro ao atualizar contrato/gráfico: " + err.message;
    }
  }

  function attachButtonFeedback() {
    document.querySelectorAll("button, a").forEach(function (el) {
      if (el.dataset.predixaiUxBound === "1") return;
      el.dataset.predixaiUxBound = "1";

      el.addEventListener("click", function () {
        const label = (el.textContent || el.value || "comando").trim();
        el.classList.remove("ux-ok", "ux-error");
        el.classList.add("ux-processing");
        showToast("Comando recebido: " + label, "ok");

        setTimeout(function () {
          el.classList.remove("ux-processing");
          el.classList.add("ux-ok");
          setTimeout(function () {
            el.classList.remove("ux-ok");
          }, 1200);
        }, 650);
      }, { capture: true });
    });
  }

  function bootUx() {
    if (document.body.dataset[UX_MARKER] === "1") return;
    document.body.dataset[UX_MARKER] = "1";
    ensureCards();
    attachButtonFeedback();
    updateContract();
    setInterval(updateContract, 3000);
    setInterval(attachButtonFeedback, 3000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootUx);
  } else {
    bootUx();
  }
})();
</script>

</body>
</html>
"""


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    for attempt in range(3):
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                return default
            return json.loads(raw)
        except OSError:
            return default
        except json.JSONDecodeError:
            if attempt == 2:
                return default
            time.sleep(0.05)
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _new_mobile_session() -> dict[str, Any]:
    now = datetime.now().astimezone()
    return {
        "session_id": f"mobile_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "started_at": now.isoformat(),
        "asset": "UNKNOWN",
        "mode": "observer_simulated",
        "orders_enabled": False,
        "created_by": "mobile_reset_session",
    }


def _read_mobile_session() -> dict[str, Any]:
    session = _read_json(MOBILE_SESSION_PATH, {})
    return session if isinstance(session, dict) else {}


def _session_id(session: dict[str, Any] | None = None) -> str:
    data = session if session is not None else _read_mobile_session()
    return _as_text(data.get("session_id")) if isinstance(data, dict) else ""


def _session_started_at(session: dict[str, Any] | None = None) -> datetime | None:
    data = session if session is not None else _read_mobile_session()
    if not isinstance(data, dict):
        return None
    return _parse_dt(data.get("started_at"))


def _write_mobile_session(session: dict[str, Any]) -> None:
    _write_json(MOBILE_SESSION_PATH, session)


def _update_mobile_session_asset(session: dict[str, Any], asset: str) -> None:
    if not session or not _is_valid_asset(asset):
        return
    if session.get("asset") == asset:
        return
    updated = {**session, "asset": asset, "updated_at": datetime.now().astimezone().isoformat()}
    _write_mobile_session(updated)


def _event_in_session(data: dict[str, Any], session: dict[str, Any]) -> bool:
    started_at = _session_started_at(session)
    if started_at is None:
        return True
    event_dt = _event_dt(data)
    if event_dt is None:
        return False
    return _dt_timestamp(event_dt) >= _dt_timestamp(started_at)


def _metadata_session_id(value: Any) -> str:
    metadata = _metadata_from_json(value)
    return _as_text(metadata.get("session_id") or metadata.get("mobile_session_id"))


def _point_session_id(point: dict[str, Any]) -> str:
    return _as_text(point.get("session_id")) or _metadata_session_id(point.get("metadata_json"))


def _point_matches_session(
    point: dict[str, Any],
    session: dict[str, Any],
    *,
    expected_asset: Any = None,
) -> bool:
    session_id = _session_id(session)
    point_session_id = _point_session_id(point)
    if session_id and point_session_id and point_session_id != session_id:
        return False

    started_at = _session_started_at(session)
    if started_at is not None:
        point_dt = _parse_dt(point.get("timestamp") or point.get("created_at"))
        if point_dt is None or _dt_timestamp(point_dt) < _dt_timestamp(started_at):
            return False

    expected_asset_text = _as_text(expected_asset)
    if _is_valid_asset(expected_asset_text):
        point_asset = _as_text(point.get("asset"))
        if not _is_valid_asset(point_asset) or point_asset.lower() != expected_asset_text.lower():
            return False

    return True


def _filter_history_scope(
    history: list[dict[str, Any]],
    session: dict[str, Any],
    *,
    asset: Any = None,
) -> list[dict[str, Any]]:
    return [
        point
        for point in history
        if _point_matches_session(point, session, expected_asset=asset)
    ]


def _runtime_backup_sources() -> list[Path]:
    if not RUNTIME_DIR.exists():
        return []
    sources: list[Path] = []
    for path in RUNTIME_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            path.relative_to(MOBILE_BACKUPS_DIR)
            continue
        except ValueError:
            pass
        sources.append(path)
    return sorted(sources)


def _create_runtime_backup(sources: list[Path]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = MOBILE_BACKUPS_DIR / f"mobile_reset_{timestamp}"
    suffix = 1
    while backup_dir.exists():
        backup_dir = MOBILE_BACKUPS_DIR / f"mobile_reset_{timestamp}_{suffix}"
        suffix += 1
    backup_dir.mkdir(parents=True, exist_ok=False)
    for source in sources:
        try:
            relative = source.relative_to(RUNTIME_DIR)
        except ValueError:
            relative = Path(source.name)
        destination = backup_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return backup_dir


def _sqlite_tables(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def _reset_sqlite_operational_tables() -> list[str]:
    _ensure_signal_db()
    tables = _sqlite_tables(SIGNALS_DB_PATH)
    reset_tables: list[str] = []
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        for table in ("signals", "price_ticks"):
            if table in tables:
                conn.execute(f"DELETE FROM {table}")
                reset_tables.append(table)
        if reset_tables and "sqlite_sequence" in tables:
            placeholders = ",".join("?" for _ in reset_tables)
            conn.execute(
                f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
                reset_tables,
            )
        conn.commit()
    return reset_tables


def _reset_mobile_session(*, dry_run: bool = False) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    sources = _runtime_backup_sources()
    planned_files = [
        str(path)
        for path in (PRICE_HISTORY_PATH, LAST_READING_PATH, REJECTED_READINGS_PATH, MOBILE_SESSION_PATH)
        if path.exists() or path in {PRICE_HISTORY_PATH, LAST_READING_PATH, REJECTED_READINGS_PATH, MOBILE_SESSION_PATH}
    ]
    planned_tables = sorted(_sqlite_tables(SIGNALS_DB_PATH) & {"signals", "price_ticks"})

    if dry_run:
        return {
            "status": "DRY_RUN",
            "backup_path": None,
            "session_id": None,
            "files_to_backup": [str(path) for path in sources],
            "files_to_clear": planned_files,
            "tables_to_clear": planned_tables,
            "message": "Rota registrada; nenhum dado real foi limpo.",
            "observer_only": True,
        }

    backup_dir = _create_runtime_backup(sources)
    session = _new_mobile_session()
    _write_mobile_session(session)
    _write_json(PRICE_HISTORY_PATH, [])
    _write_json(REJECTED_READINGS_PATH, [])
    _write_json(
        LAST_READING_PATH,
        {
            "status": "SESSION_RESET",
            "source": "mobile_reset_session",
            "session_id": session["session_id"],
            "timestamp": session["started_at"],
            "asset": "UNKNOWN",
            "price": "UNKNOWN",
            "price_value": None,
            "confidence": 0.0,
            "unknown_fields": [],
            "message": "Sessão limpa criada com backup; aguardando nova leitura.",
            "observer_only": True,
            "orders_enabled": False,
        },
    )
    reset_tables = _reset_sqlite_operational_tables()
    return {
        "status": "RESET_OK",
        "backup_path": str(backup_dir),
        "session_id": session["session_id"],
        "files_backed_up": [str(path) for path in sources],
        "files_cleared": planned_files,
        "tables_cleared": reset_tables,
        "message": "Sessão limpa criada com backup.",
        "observer_only": True,
    }


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "sim", "on"}


def _number(value: Any, default: float) -> float:
    parsed = _parse_float(value)
    return default if parsed is None else float(parsed)


def _int_number(value: Any, default: int) -> int:
    try:
        return int(_number(value, float(default)))
    except (TypeError, ValueError):
        return default


def _block(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    return value if isinstance(value, dict) else {}


def _safe_choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip().upper()
    return text if text in allowed else default


def _simulated_contract_config(payload: dict[str, Any]) -> dict[str, Any]:
    session = _block(payload, "session")
    strategy = _block(payload, "strategy")
    bankroll = _block(payload, "bankroll")
    risk = _block(payload, "risk")
    operation = _block(payload, "operation")
    recovery = _block(payload, "recovery")

    strategy_mode = _safe_choice(
        strategy.get("primary_strategy") or strategy.get("strategy_mode"),
        ALLOWED_SIMULATED_STRATEGIES,
        "LEGACY_MOMENTUM",
    )
    risk_profile = _safe_choice(
        risk.get("risk_profile"),
        ALLOWED_SIMULATED_RISK_PROFILES,
        "CONSERVATIVE",
    )
    recovery_enabled = _as_bool(recovery.get("recovery_enabled"), False)
    recovery_mode = str(recovery.get("recovery_mode") or "NONE").upper().strip()
    if recovery_mode == "MULTIPLIER":
        recovery_mode = "SOFT_MARTINGALE"
    if not recovery_enabled:
        recovery_mode = "NONE"

    initial_bankroll = max(1.0, _number(bankroll.get("initial_bankroll"), 100.0))
    current_bankroll = max(0.0, _number(bankroll.get("current_bankroll"), initial_bankroll))
    initial_entry = max(1.0, _number(bankroll.get("initial_entry"), 5.0))
    current_entry = max(1.0, _number(bankroll.get("current_entry"), initial_entry))
    current_entry = min(current_entry, max(current_bankroll, 1.0))

    return {
        "session": {
            "status": "RUNNING",
            "started_at": _now_iso(),
            "session_type": _safe_choice(session.get("session_type"), {"SCALPER", "DAY_TRADE", "TEST", "TRAINING"}, "TEST"),
        },
        "config": {
            "session_notes": session.get("session_name") or "PTP-113 simulated mobile-first bridge",
            "broker_mode": "SIMULATED_ONLY",
            "start_mode": "MOBILE_SIMULATED_START",
        },
        "strategy": {
            "strategy_mode": strategy_mode,
            "strategy_stack": [strategy_mode],
            "confluence_required": True,
            "min_confidence": max(50, min(95, _int_number(strategy.get("min_confidence"), 70))),
        },
        "bankroll": {
            "initial_bankroll": round(initial_bankroll, 2),
            "current_bankroll": round(current_bankroll, 2),
            "initial_entry": round(min(initial_entry, initial_bankroll), 2),
            "current_entry": round(current_entry, 2),
            "profit_loss": 0.0,
            "profit_loss_percent": 0.0,
        },
        "risk": {
            "risk_profile": risk_profile,
            "stop_loss": max(1.0, min(_number(risk.get("stop_loss"), 20.0), initial_bankroll)),
            "take_profit": max(1.0, _number(risk.get("take_profit"), 20.0)),
            "max_signals": max(1, min(100, _int_number(risk.get("max_signals"), 10))),
            "max_losses": max(1, min(20, _int_number(risk.get("max_losses"), 3))),
            "payout_min": max(50, min(100, _int_number(operation.get("payout_min") or risk.get("payout_min"), 80))),
            "payout_source": "MANUAL",
        },
        "operation": {
            "expiration_seconds": max(30, _int_number(operation.get("expiration_seconds"), DEFAULT_EXPIRATION_SECONDS)),
            "paper_trade_enabled": True,
            "allow_multiple_open_trades": False,
            "max_open_trades": 1,
        },
        "recovery": {
            "recovery_enabled": recovery_enabled,
            "recovery_mode": recovery_mode,
            "max_recovery_steps": 0 if not recovery_enabled else max(0, min(5, _int_number(recovery.get("max_recovery_steps"), 0))),
            "current_recovery_step": 0,
            "recovery_multiplier": max(1.0, min(3.0, _number(recovery.get("recovery_multiplier"), 1.0))),
        },
    }


def _simulated_market_payload(payload: dict[str, Any]) -> tuple[str, float, float, list[float]]:
    market = _block(payload, "simulated_market")
    asset = _as_text(market.get("asset")) or DEFAULT_SIMULATED_ASSET
    if not _is_valid_asset(asset):
        asset = DEFAULT_SIMULATED_ASSET

    previous_price = _number(market.get("previous_price"), 4100.00)
    current_price = _number(market.get("current_price"), 4182.10)
    if not _is_valid_price(previous_price, asset):
        previous_price = 4100.00
    if not _is_valid_price(current_price, asset):
        current_price = 4182.10

    recent_values = market.get("recent_prices")
    recent_prices: list[float] = []
    if isinstance(recent_values, list):
        for item in recent_values:
            parsed = _parse_float(item)
            if _is_valid_price(parsed, asset):
                recent_prices.append(float(parsed))

    if len(recent_prices) < 6:
        step = (current_price - previous_price) / 5 or 0.15
        recent_prices = [round(previous_price + step * idx, 6) for idx in range(6)]
        recent_prices[-1] = current_price

    return asset, float(previous_price), float(current_price), recent_prices[-6:]


def _write_simulated_history_points(
    *,
    session_id: str,
    asset: str,
    recent_prices: list[float],
    mobile_signal: dict[str, Any],
    paper_trade: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_history = _read_json(PRICE_HISTORY_PATH, [])
    if not isinstance(raw_history, list):
        raw_history = []

    base_time = _now()
    points: list[dict[str, Any]] = []
    for index, price in enumerate(recent_prices):
        timestamp = (base_time - timedelta(seconds=(len(recent_prices) - index - 1) * 3)).isoformat()
        point = {
            "timestamp": timestamp,
            "session_id": session_id,
            "asset": asset,
            "price": _format_price_value(price),
            "price_value": _format_price_value(price),
            "confidence": mobile_signal.get("confidence"),
            "status": "SIMULATED",
            "source": SIMULATED_BRIDGE_SOURCE,
            "simulation_only": True,
            "observer_only": True,
            "orders_enabled": False,
            "auto_click_enabled": False,
            "real_money_enabled": False,
            "mobile_signal": mobile_signal,
            "paper_trade_session": paper_trade,
        }
        raw_history.append(point)
        points.append(point)

    _write_json(PRICE_HISTORY_PATH, raw_history[-3000:])
    _ensure_signal_db()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        for point in points:
            conn.execute(
                """
                INSERT INTO price_ticks (created_at, asset, price, source, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    point["timestamp"],
                    asset,
                    float(point["price_value"]),
                    SIMULATED_BRIDGE_SOURCE,
                    json.dumps(
                        {
                            "session_id": session_id,
                            "simulation_only": True,
                            "orders_enabled": False,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()
    return points


def _persist_paper_trade_signal(
    *,
    session_id: str,
    asset: str,
    price: float,
    mobile_signal: dict[str, Any],
    paper_trade: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    operations = paper_trade.get("operations") if isinstance(paper_trade, dict) else []
    if not operations:
        return

    operation = operations[0]
    direction = str(operation.get("direction") or mobile_signal.get("decision") or "").upper()
    if direction not in {"ALTA", "BAIXA"}:
        return

    _ensure_signal_db()
    created_at = _now_iso()
    metadata = {
        "session_id": session_id,
        "simulation_only": True,
        "observer_only": True,
        "orders_enabled": False,
        "auto_click_enabled": False,
        "real_money_enabled": False,
        "paper_trade_session": paper_trade,
        "mobile_signal": mobile_signal,
        "contract_version": contract.get("session", {}).get("contract_version"),
    }
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO signals (
                created_at, asset, price, signal, direction, confidence,
                expiration_seconds, reason, source, status, result,
                session_id, metadata_json, entry_price, support, resistance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                asset,
                _format_price_value(price),
                f"OBSERVAR {direction}",
                direction,
                float(mobile_signal.get("confidence") or 0),
                _normalize_expiration_seconds(contract.get("operation", {}).get("expiration_seconds")),
                "PaperTradeSession simulado iniciado por /mobile/session/start.",
                SIMULATED_BRIDGE_SOURCE,
                "PENDING",
                "PENDING",
                session_id,
                json.dumps(metadata, ensure_ascii=False),
                _format_price_value(price),
                None,
                None,
            ),
        )
        conn.commit()


def _start_simulated_mobile_session(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    contract = build_mobile_session_contract(_simulated_contract_config(payload))
    ok, errors = validate_mobile_session_contract(contract)
    if not ok:
        return {
            "ok": False,
            "status": "VALIDATION_FAILED",
            "errors": errors,
            "observer_only": True,
            "simulation_only": True,
            "orders_enabled": False,
        }

    asset, previous_price, current_price, recent_prices = _simulated_market_payload(payload)
    strategy_input = StrategyInput(
        asset=asset,
        current_price=current_price,
        previous_price=previous_price,
        recent_prices=recent_prices,
    )
    strategy_decision = MinimalStrategyEngine().analyze(strategy_input)
    minimum_confidence = float(contract.get("strategy", {}).get("min_confidence", 70))
    confluence_result = ConfluenceEngine(minimum_confidence=minimum_confidence).evaluate(strategy_decision)
    mobile_screen = build_mobile_signal_screen(confluence_result)
    entry_value = float(contract.get("bankroll", {}).get("current_entry", 5.0))
    initial_balance = float(contract.get("bankroll", {}).get("initial_bankroll", 100.0))
    session_id = str(contract["session"]["session_id"])
    paper_session = build_paper_trade_from_mobile_signal(
        mobile_screen,
        session_id=session_id,
        entry_value=entry_value,
        initial_balance=initial_balance,
    )

    mobile_signal = mobile_screen.to_dict()
    paper_trade = paper_session.to_dict()
    session_payload = {
        "session_id": session_id,
        "started_at": contract["session"]["started_at"],
        "asset": asset,
        "mode": "mobile_first_simulated",
        "source": SIMULATED_BRIDGE_SOURCE,
        "orders_enabled": False,
        "auto_click_enabled": False,
        "real_money_enabled": False,
        "broker_login_enabled": False,
        "simulation_only": True,
        "contract": contract,
        "strategy_decision": strategy_decision.to_dict(),
        "confluence_result": confluence_result.to_dict(),
        "mobile_signal": mobile_signal,
        "paper_trade_session": paper_trade,
    }
    _write_mobile_session(session_payload)
    history_points = _write_simulated_history_points(
        session_id=session_id,
        asset=asset,
        recent_prices=recent_prices,
        mobile_signal=mobile_signal,
        paper_trade=paper_trade,
    )
    _persist_paper_trade_signal(
        session_id=session_id,
        asset=asset,
        price=current_price,
        mobile_signal=mobile_signal,
        paper_trade=paper_trade,
        contract=contract,
    )
    _write_json(
        LAST_READING_PATH,
        {
            "status": "SIMULATED_SESSION_READY",
            "source": SIMULATED_BRIDGE_SOURCE,
            "timestamp": _now_iso(),
            "session_id": session_id,
            "asset": asset,
            "price": _format_price_value(current_price),
            "price_value": _format_price_value(current_price),
            "signal": f"OBSERVAR {mobile_signal['decision']}" if mobile_signal["decision"] in {"ALTA", "BAIXA"} else "AGUARDAR",
            "direction": mobile_signal["decision"],
            "confidence": mobile_signal["confidence"],
            "reason": confluence_result.reason,
            "observer_only": True,
            "simulation_only": True,
            "orders_enabled": False,
            "auto_click_enabled": False,
            "real_money_enabled": False,
            "mobile_signal": mobile_signal,
            "paper_trade_session": paper_trade,
        },
    )

    return {
        "ok": True,
        "status": "SIMULATED_SESSION_STARTED",
        "session_id": session_id,
        "observer_only": True,
        "simulation_only": True,
        "orders_enabled": False,
        "auto_click_enabled": False,
        "real_money_enabled": False,
        "asset": asset,
        "source": SIMULATED_BRIDGE_SOURCE,
        "strategy_decision": strategy_decision.to_dict(),
        "confluence_result": confluence_result.to_dict(),
        "mobile_signal": mobile_signal,
        "paper_trade_session": paper_trade,
        "history_points": len(history_points),
        "runtime": {
            "mobile_session": str(MOBILE_SESSION_PATH),
            "last_live_reading": str(LAST_READING_PATH),
            "live_price_history": str(PRICE_HISTORY_PATH),
            "signals_db": str(SIGNALS_DB_PATH),
        },
    }


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
    if asset is not None and not _is_valid_asset(asset):
        return False
    if int(round(value)) in {1, 3, 24, 25, 52, 85, 2026}:
        return False
    asset_text = (asset or "").lower()
    min_price = 100.0 if "latam" in asset_text else 1000.0
    if value < min_price:
        return False
    if ("cafe" in asset_text or "asia composite" in asset_text) and 1900 <= value <= 2100:
        return False
    return True


def _is_valid_asset(asset: Any) -> bool:
    text = str(asset or "").strip()
    if text.upper() in {"", "UNKNOWN", "DATA", "NONE", "N/A", "-"}:
        return False

    lowered = text.lower()
    if any(token in lowered for token in ("core/", "core\\", "codex", "powershell", "visual studio code")):
        return False
    return "index" in lowered


def _format_price_value(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _normalize_expiration_seconds(value: Any = None) -> int:
    try:
        seconds = int(str(value if value is not None else DEFAULT_EXPIRATION_SECONDS).strip())
    except (TypeError, ValueError):
        return DEFAULT_EXPIRATION_SECONDS
    if seconds in ALLOWED_EXPIRATION_SECONDS:
        return seconds
    return DEFAULT_EXPIRATION_SECONDS


def _stored_expiration_seconds(value: Any = None) -> int:
    try:
        seconds = int(str(value if value is not None else DEFAULT_EXPIRATION_SECONDS).strip())
    except (TypeError, ValueError):
        return DEFAULT_EXPIRATION_SECONDS
    return seconds if seconds > 0 else DEFAULT_EXPIRATION_SECONDS


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


def _dt_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=_now().tzinfo)
    return value.timestamp()


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat()


def _file_age_seconds(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(max(0, time.time() - path.stat().st_mtime))


def _path_mtime(path: Path) -> float | None:
    if not path.exists():
        return None
    return path.stat().st_mtime


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


def _event_dt(data: Any) -> datetime | None:
    return _parse_dt(_extract_value(data, {"timestamp", "created_at", "captured_at", "updated_at", "time"}))


def _latest_rejection(rejected: list[Any]) -> dict[str, Any] | None:
    for item in reversed(rejected):
        if isinstance(item, dict):
            return item
    return None


def _latest_event_is_rejection(last: dict[str, Any], latest_rejection: dict[str, Any] | None) -> bool:
    if latest_rejection is None:
        return False

    rejection_dt = _event_dt(latest_rejection)
    last_dt = _event_dt(last)
    if rejection_dt is not None and last_dt is not None:
        return rejection_dt >= last_dt

    rejection_mtime = _path_mtime(REJECTED_READINGS_PATH)
    last_mtime = _path_mtime(LAST_READING_PATH)
    return rejection_mtime is not None and (last_mtime is None or rejection_mtime >= last_mtime)


def _collect_price_history(limit: int | None = HISTORY_LIMIT) -> list[dict[str, Any]]:
    raw_history = _read_json(PRICE_HISTORY_PATH, [])
    if not isinstance(raw_history, list):
        raw_history = []

    points: list[dict[str, Any]] = []
    source_history = raw_history if limit is None else raw_history[-3000:]
    for index, item in enumerate(source_history, start=1):
        if not isinstance(item, dict):
            continue
        asset = _as_text(item.get("asset")) or _asset_from_text(item)
        price = _parse_float(item.get("price_value"))
        if price is None:
            price = _parse_float(item.get("price"))
        if not _is_valid_price(price, asset):
            continue
        point = {
            "index": index,
            "timestamp": item.get("timestamp"),
            "session_id": item.get("session_id"),
            "asset": asset or "UNKNOWN",
            "price": _format_price_value(price),
            "price_value": _format_price_value(price),
            "confidence": _parse_float(item.get("confidence")),
            "status": item.get("status"),
            "source": item.get("source"),
            "window_title": item.get("window_title"),
            "source_ocr_text": item.get("source_ocr_text"),
            "metadata_json": item.get("metadata_json"),
        }
        if _valid_price_point(point) is None:
            continue
        points.append(point)
    return points[-limit:] if limit is not None else points


def _collect_history() -> list[dict[str, Any]]:
    return _collect_price_history(HISTORY_LIMIT)


def _support_resistance(history: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    prices = [
        float(point["price_value"])
        for point in history
        if isinstance(point.get("price_value"), (int, float))
    ]
    if not prices:
        return None, None
    return _format_price_value(min(prices)), _format_price_value(max(prices))


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
                result_reason TEXT,
                session_id TEXT,
                metadata_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                asset TEXT,
                price REAL NOT NULL,
                source TEXT,
                metadata_json TEXT
            )
            """
        )
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(signals)").fetchall()
        }
        for column_name, column_type in {
            "entry_price": "REAL",
            "support": "REAL",
            "resistance": "REAL",
            "result_reason": "TEXT",
            "session_id": "TEXT",
        }.items():
            if column_name not in columns:
                conn.execute(f"ALTER TABLE signals ADD COLUMN {column_name} {column_type}")
        conn.commit()


def _metadata_from_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _invalid_window_text(value: Any) -> bool:
    text = str(value or "").lower()
    if not text:
        return False
    invalid_markers = (
        "codex",
        "powershell",
        "pwsh",
        "visual studio code",
        "cmd.exe",
        "command prompt",
        "terminal",
        "predixai compact",
        "predixai trader mobile",
        "localhost:8766",
        "127.0.0.1:8766",
        "localhost:8765",
        "127.0.0.1:8765",
        "dashboard",
    )
    return any(marker in text for marker in invalid_markers)


def _point_metadata(point: dict[str, Any]) -> dict[str, Any]:
    metadata = _metadata_from_json(point.get("metadata_json"))
    broker_window = metadata.get("broker_window")
    if isinstance(broker_window, dict):
        broker_metadata = broker_window.get("metadata")
        if isinstance(broker_metadata, dict):
            metadata["broker_window_valid"] = broker_metadata.get("broker_window_valid")
    return metadata


def _point_window_text(point: dict[str, Any]) -> str:
    metadata = _point_metadata(point)
    parts = [
        point.get("window_title"),
        point.get("source_ocr_text"),
        metadata.get("window_title"),
    ]
    broker_window = metadata.get("broker_window")
    if isinstance(broker_window, dict):
        parts.append(broker_window.get("title"))
    return " ".join(str(part or "") for part in parts).strip()


def _valid_price_point(
    point: dict[str, Any],
    *,
    expected_asset: Any = None,
) -> tuple[datetime, float] | None:
    point_dt = _parse_dt(point.get("timestamp") or point.get("created_at"))
    if point_dt is None:
        return None

    asset = _as_text(point.get("asset"))
    expected_asset_text = _as_text(expected_asset)
    validation_asset = asset or expected_asset_text
    price = _parse_float(point.get("price_value"))
    if price is None:
        price = _parse_float(point.get("price"))
    if not _is_valid_price(price, validation_asset):
        return None

    if expected_asset_text and _is_valid_asset(expected_asset_text):
        if asset and _is_valid_asset(asset) and asset.lower() != expected_asset_text.lower():
            return None

    metadata = _point_metadata(point)
    if metadata.get("broker_window_valid") is False:
        return None
    if _invalid_window_text(_point_window_text(point)):
        return None

    source = str(point.get("source") or "").lower()
    if any(marker in source for marker in ("codex", "powershell", "vscode", "dashboard", "compact")):
        return None

    return point_dt, float(price)


def _no_result_price_metadata(target_dt: datetime) -> dict[str, Any]:
    return {
        "result_reason": UNKNOWN_NO_HISTORY_REASON,
        "target_time": target_dt.isoformat(),
        "search_window_end": (
            target_dt + timedelta(seconds=RESULT_PRICE_TOLERANCE_SECONDS)
        ).isoformat(),
        "tolerance_seconds": RESULT_PRICE_TOLERANCE_SECONDS,
        "result_price_search_status": "WAITING_RESULT",
        "result_price_source": "none",
    }


def _price_from_points_near_target(
    points: list[dict[str, Any]],
    target_dt: datetime,
    *,
    source_name: str,
    expected_asset: Any = None,
) -> tuple[float | None, dict[str, Any]]:
    target_ts = _dt_timestamp(target_dt)
    future_matches: list[tuple[float, float, dict[str, Any]]] = []
    nearest_matches: list[tuple[float, float, dict[str, Any]]] = []

    for point in points:
        parsed = _valid_price_point(point, expected_asset=expected_asset)
        if parsed is None:
            continue
        point_dt, price = parsed
        diff_seconds = _dt_timestamp(point_dt) - target_ts
        abs_diff = abs(diff_seconds)
        if abs_diff > RESULT_PRICE_TOLERANCE_SECONDS:
            continue
        candidate = (abs_diff, diff_seconds, {**point, "price_value": price})
        nearest_matches.append(candidate)
        if diff_seconds >= 0:
            future_matches.append(candidate)

    matches = future_matches or nearest_matches
    if not matches:
        return None, _no_result_price_metadata(target_dt)

    _, diff_seconds, point = sorted(matches, key=lambda item: (item[0], abs(item[1])))[0]
    price = _parse_float(point.get("price_value"))
    return price, {
        "result_reason": "",
        "target_time": target_dt.isoformat(),
        "search_window_end": (
            target_dt + timedelta(seconds=RESULT_PRICE_TOLERANCE_SECONDS)
        ).isoformat(),
        "result_price_timestamp": point.get("timestamp") or point.get("created_at"),
        "result_price_delta_seconds": round(diff_seconds, 3),
        "result_price_match": (
            "first_at_or_after_target" if diff_seconds >= 0 else "nearest_within_tolerance"
        ),
        "result_price_search_status": "FOUND",
        "result_price_source": source_name,
    }


def _insert_price_tick(
    *,
    created_at: str,
    asset: str,
    price: float,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    _ensure_signal_db()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO price_ticks (
                created_at, asset, price, source, metadata_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at,
                asset,
                price,
                source,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _history_price_near_target(
    history: list[dict[str, Any]],
    target_dt: datetime,
    expected_asset: Any = None,
) -> tuple[float | None, dict[str, Any]]:
    return _price_from_points_near_target(
        history,
        target_dt,
        source_name="json",
        expected_asset=expected_asset,
    )


def _sqlite_price_tick_near_target(
    target_dt: datetime,
    expected_asset: Any = None,
) -> tuple[float | None, dict[str, Any]]:
    _ensure_signal_db()
    points: list[dict[str, Any]] = []
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT created_at, asset, price, source, metadata_json
            FROM price_ticks
            ORDER BY id ASC
            """
        ).fetchall()
    for row in rows:
        points.append(
            {
                "timestamp": row["created_at"],
                "created_at": row["created_at"],
                "asset": row["asset"],
                "price": row["price"],
                "price_value": row["price"],
                "source": row["source"],
                "metadata_json": row["metadata_json"],
            }
        )
    return _price_from_points_near_target(
        points,
        target_dt,
        source_name="sqlite_price_ticks",
        expected_asset=expected_asset,
    )


def _result_price_near_target(
    history: list[dict[str, Any]],
    target_dt: datetime,
    expected_asset: Any = None,
) -> tuple[float | None, dict[str, Any]]:
    price, metadata = _history_price_near_target(
        history,
        target_dt,
        expected_asset=expected_asset,
    )
    if price is not None:
        return price, metadata

    sqlite_price, sqlite_metadata = _sqlite_price_tick_near_target(
        target_dt,
        expected_asset=expected_asset,
    )
    if sqlite_price is not None:
        return sqlite_price, sqlite_metadata
    return None, metadata


def _evaluate_signal_result(
    direction: Any,
    entry_price: float | None,
    result_price: float | None,
) -> tuple[str, float | None]:
    if entry_price is None or result_price is None:
        return "UNKNOWN", None

    delta = result_price - entry_price
    if abs(delta) < 0.000001:
        return "DRAW", delta

    direction_text = str(direction or "").upper()
    if direction_text == "ALTA":
        return ("WIN" if delta > 0 else "LOSS"), delta
    if direction_text == "BAIXA":
        return ("WIN" if delta < 0 else "LOSS"), delta
    return "UNKNOWN", delta


def _check_pending_signals(history: list[dict[str, Any]]) -> None:
    _ensure_signal_db()
    now = _now()
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT *
            FROM signals
            WHERE status IN ('WAITING_RESULT', 'PENDING')
            ORDER BY id ASC
            """
        ).fetchall()
        for row in rows:
            created_at = _parse_dt(row["created_at"])
            if created_at is None:
                continue
            expiration_seconds = _stored_expiration_seconds(row["expiration_seconds"])
            target_dt = created_at + timedelta(seconds=expiration_seconds)
            if _dt_timestamp(now) < _dt_timestamp(target_dt):
                if row["status"] != WAITING_RESULT_STATUS:
                    conn.execute(
                        "UPDATE signals SET status = ?, result = ? WHERE id = ?",
                        (WAITING_RESULT_STATUS, WAITING_RESULT_STATUS, row["id"]),
                    )
                continue

            entry_price = _parse_float(row["entry_price"])
            if entry_price is None:
                entry_price = _parse_float(row["price"])
            result_price, match_metadata = _result_price_near_target(
                history,
                target_dt,
                expected_asset=row["asset"],
            )
            metadata = _metadata_from_json(row["metadata_json"])
            metadata.update(match_metadata)

            unknown_deadline = target_dt + timedelta(seconds=UNKNOWN_AFTER_EXPIRATION_SECONDS)
            if result_price is None and _dt_timestamp(now) < _dt_timestamp(unknown_deadline):
                metadata["result_price_search_status"] = WAITING_RESULT_STATUS
                metadata["unknown_after"] = unknown_deadline.isoformat()
                conn.execute(
                    """
                    UPDATE signals
                    SET status = ?,
                        result = ?,
                        metadata_json = ?
                    WHERE id = ?
                    """,
                    (
                        WAITING_RESULT_STATUS,
                        WAITING_RESULT_STATUS,
                        json.dumps(metadata, ensure_ascii=False),
                        row["id"],
                    ),
                )
                continue

            result, delta = _evaluate_signal_result(row["direction"], entry_price, result_price)
            result_reason = UNKNOWN_NO_HISTORY_REASON if result == "UNKNOWN" else ""
            metadata["result_reason"] = result_reason
            metadata["unknown_after"] = unknown_deadline.isoformat()
            if result == "UNKNOWN":
                metadata["result_price_search_status"] = "UNKNOWN_AFTER_MARGIN"

            conn.execute(
                """
                UPDATE signals
                SET status = ?,
                    result = ?,
                    result_checked_at = ?,
                    result_price = ?,
                    delta = ?,
                    result_reason = ?,
                    metadata_json = ?
                WHERE id = ?
                """,
                (
                    result,
                    result,
                    _now_iso(),
                    result_price,
                    delta,
                    result_reason,
                    json.dumps(metadata, ensure_ascii=False),
                    row["id"],
                ),
            )
        conn.commit()


def _backfill_unknown_signals(history: list[dict[str, Any]]) -> int:
    _ensure_signal_db()
    updated = 0
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT *
            FROM signals
            WHERE (status = 'UNKNOWN' OR result = 'UNKNOWN')
              AND result_price IS NULL
            ORDER BY id ASC
            """
        ).fetchall()
        for row in rows:
            created_at = _parse_dt(row["created_at"])
            entry_price = _parse_float(row["entry_price"])
            if entry_price is None:
                entry_price = _parse_float(row["price"])
            expiration_seconds = _stored_expiration_seconds(row["expiration_seconds"])
            if created_at is None or entry_price is None or not expiration_seconds:
                continue

            target_dt = created_at + timedelta(seconds=expiration_seconds)
            result_price, match_metadata = _result_price_near_target(
                history,
                target_dt,
                expected_asset=row["asset"],
            )
            if result_price is None:
                continue

            result, delta = _evaluate_signal_result(row["direction"], entry_price, result_price)
            metadata = _metadata_from_json(row["metadata_json"])
            metadata.update(match_metadata)
            metadata["backfilled_unknown"] = True
            metadata["result_reason"] = ""
            conn.execute(
                """
                UPDATE signals
                SET status = ?,
                    result = ?,
                    result_checked_at = ?,
                    result_price = ?,
                    delta = ?,
                    result_reason = ?,
                    metadata_json = ?
                WHERE id = ?
                """,
                (
                    result,
                    result,
                    _now_iso(),
                    result_price,
                    delta,
                    "",
                    json.dumps(metadata, ensure_ascii=False),
                    row["id"],
                ),
            )
            updated += 1
        conn.commit()
    return updated


def _normalize_signal_result_consistency() -> int:
    _ensure_signal_db()
    updated = 0
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, status, result, result_price, direction, entry_price, price
            FROM signals
            WHERE result IN ('WIN', 'LOSS', 'DRAW')
               OR ((status = 'UNKNOWN' OR result = 'UNKNOWN') AND result_price IS NOT NULL)
            ORDER BY id ASC
            """
        ).fetchall()
        for row in rows:
            result = str(row["result"] or "").upper()
            if result not in {"WIN", "LOSS", "DRAW"}:
                entry_price = _parse_float(row["entry_price"])
                if entry_price is None:
                    entry_price = _parse_float(row["price"])
                result_price = _parse_float(row["result_price"])
                result, delta = _evaluate_signal_result(row["direction"], entry_price, result_price)
                if result not in {"WIN", "LOSS", "DRAW"}:
                    continue
                conn.execute(
                    """
                    UPDATE signals
                    SET status = ?,
                        result = ?,
                        delta = ?,
                        result_reason = ''
                    WHERE id = ?
                    """,
                    (result, result, delta, row["id"]),
                )
            elif str(row["status"] or "").upper() != result:
                conn.execute(
                    """
                    UPDATE signals
                    SET status = ?,
                        result = ?,
                        result_reason = ''
                    WHERE id = ?
                    """,
                    (result, result, row["id"]),
                )
            else:
                continue
            updated += 1
        conn.commit()
    return updated


def _register_signal_if_needed(state: dict[str, Any], expiration_seconds: int) -> None:
    signal = str(state.get("signal") or "")
    if signal not in {"OBSERVAR ALTA", "OBSERVAR BAIXA"}:
        return

    asset = str(state.get("asset") or "UNKNOWN")
    direction = "ALTA" if "ALTA" in signal else "BAIXA"
    price = _parse_float(state.get("price"))
    if not _is_valid_price(price, asset):
        return

    expiration_seconds = _normalize_expiration_seconds(expiration_seconds)
    support = _parse_float(state.get("support"))
    resistance = _parse_float(state.get("resistance"))
    _ensure_signal_db()
    now = _now()
    session = _read_mobile_session()
    session_id = _session_id(session)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if session_id:
            pending = conn.execute(
                """
                SELECT id
                FROM signals
                WHERE asset = ?
                  AND direction = ?
                  AND session_id = ?
                  AND status IN ('WAITING_RESULT', 'PENDING')
                LIMIT 1
                """,
                (asset, direction, session_id),
            ).fetchone()
        else:
            pending = conn.execute(
                """
                SELECT id
                FROM signals
                WHERE asset = ?
                  AND direction = ?
                  AND status IN ('WAITING_RESULT', 'PENDING')
                LIMIT 1
                """,
                (asset, direction),
            ).fetchone()
        if pending:
            return

        if session_id:
            row = conn.execute(
                """
                SELECT created_at
                FROM signals
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT created_at
                FROM signals
                ORDER BY id DESC
                LIMIT 1
                """,
            ).fetchone()
        if row:
            last_created = _parse_dt(row["created_at"])
            if last_created is not None:
                elapsed = _dt_timestamp(now) - _dt_timestamp(last_created)
                if elapsed < SIGNAL_COOLDOWN_SECONDS:
                    return

        metadata = {
            "observer_only": True,
            "financial_advice": False,
            "orders_enabled": False,
            "history_count": state.get("valid_readings", 0),
            "expiration_seconds": expiration_seconds,
            "support": support,
            "resistance": resistance,
            "session_id": session_id,
            "session_started_at": session.get("started_at"),
        }
        created_at = _now_iso()
        conn.execute(
            """
            INSERT INTO signals (
                created_at, asset, price, signal, direction, confidence,
                expiration_seconds, reason, source, status, result,
                session_id, metadata_json, entry_price, support, resistance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                asset,
                price,
                signal,
                direction,
                _parse_float(state.get("confidence")),
                expiration_seconds,
                state.get("reason"),
                "mobile_server",
                WAITING_RESULT_STATUS,
                WAITING_RESULT_STATUS,
                session_id or None,
                json.dumps(metadata, ensure_ascii=False),
                price,
                support,
                resistance,
            ),
        )
        conn.commit()


def _decorate_signal(row: Any) -> dict[str, Any]:
    item = dict(row)
    metadata = _metadata_from_json(item.get("metadata_json"))
    expiration_seconds = _stored_expiration_seconds(item.get("expiration_seconds"))
    item["expiration_seconds"] = expiration_seconds
    item["emitted_at"] = item.get("created_at")
    item["entry_price"] = _format_price_value(
        _parse_float(item.get("entry_price")) or _parse_float(item.get("price"))
    )
    item["price"] = item["entry_price"]
    item["support"] = _format_price_value(_parse_float(item.get("support")))
    item["resistance"] = _format_price_value(_parse_float(item.get("resistance")))
    item["result_price"] = _format_price_value(_parse_float(item.get("result_price")))
    item["delta"] = _format_price_value(_parse_float(item.get("delta")))
    item["result_price_timestamp"] = metadata.get("result_price_timestamp")
    item["result_price_delta_seconds"] = metadata.get("result_price_delta_seconds")
    item["result_price_source"] = metadata.get("result_price_source")
    item["session_id"] = item.get("session_id") or metadata.get("session_id")
    item["target_time"] = metadata.get("target_time")
    item["search_window_end"] = metadata.get("search_window_end")
    item["unknown_after"] = metadata.get("unknown_after")
    item["result_price_search_status"] = metadata.get("result_price_search_status")
    item["result_reason"] = item.get("result_reason") or metadata.get("result_reason") or ""
    if (item.get("result") == "UNKNOWN" or item.get("status") == "UNKNOWN") and not item["result_reason"]:
        item["result_reason"] = UNKNOWN_NO_HISTORY_REASON
    item["unknown_reason"] = item["result_reason"] if item.get("result") == "UNKNOWN" else ""

    created_at = _parse_dt(item.get("created_at"))
    if created_at is None:
        item["expires_at"] = None
        item["remaining_seconds"] = None
        return item

    expires_at = created_at + timedelta(seconds=expiration_seconds)
    item["expires_at"] = expires_at.isoformat()
    if item.get("status") in {"PENDING", WAITING_RESULT_STATUS}:
        remaining = _dt_timestamp(expires_at) - _dt_timestamp(_now())
        item["remaining_seconds"] = int(max(0, remaining + 0.999))
    else:
        item["remaining_seconds"] = 0
    return item


def _signal_scope_where(
    session: dict[str, Any] | None = None,
    asset: Any = None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    session = session or {}
    session_id = _session_id(session)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    else:
        started_at = _session_started_at(session)
        if started_at is not None:
            clauses.append("created_at >= ?")
            params.append(started_at.isoformat())

    asset_text = _as_text(asset)
    if _is_valid_asset(asset_text):
        clauses.append("asset = ?")
        params.append(asset_text)

    return (" WHERE " + " AND ".join(clauses), params) if clauses else ("", params)


def _list_signals(
    session: dict[str, Any] | None = None,
    asset: Any = None,
) -> list[dict[str, Any]]:
    _ensure_signal_db()
    where_sql, params = _signal_scope_where(session, asset)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT id, created_at, asset, price, signal, direction, confidence,
                   expiration_seconds, reason, status, result_checked_at,
                   result_price, result, delta, entry_price, support, resistance,
                   result_reason, session_id, source, metadata_json
            FROM signals
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, SIGNALS_LIMIT),
        ).fetchall()
        return [_decorate_signal(row) for row in rows]


def _hit_rate_percent(win: int, loss: int, draw: int) -> float:
    valid = win + loss + draw
    return round((win / valid) * 100, 1) if valid else 0.0


def _signal_stats(
    session: dict[str, Any] | None = None,
    asset: Any = None,
) -> dict[str, Any]:
    _ensure_signal_db()
    where_sql, params = _signal_scope_where(session, asset)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) AS win,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) AS loss,
                SUM(CASE WHEN result = 'DRAW' THEN 1 ELSE 0 END) AS draw,
                SUM(CASE WHEN result = 'UNKNOWN' THEN 1 ELSE 0 END) AS unknown,
                SUM(CASE WHEN status IN ('WAITING_RESULT', 'PENDING') THEN 1 ELSE 0 END) AS pending
            FROM signals
            {where_sql}
            """,
            params,
        ).fetchone()
        latest = conn.execute(
            f"""
            SELECT id, created_at, asset, price, signal, direction, confidence,
                   expiration_seconds, reason, status, result_checked_at,
                   result_price, result, delta, entry_price, support, resistance,
                   result_reason, session_id, source, metadata_json
            FROM signals
            {where_sql}
            ORDER BY id DESC
            LIMIT 1
            """,
            params,
        ).fetchone()

    total = int(row["total"] or 0)
    win = int(row["win"] or 0)
    loss = int(row["loss"] or 0)
    draw = int(row["draw"] or 0)
    unknown = int(row["unknown"] or 0)
    pending = int(row["pending"] or 0)
    closed = win + loss + draw + unknown
    hit_rate = _hit_rate_percent(win, loss, draw)
    return {
        "total": total,
        "closed": closed,
        "win": win,
        "loss": loss,
        "draw": draw,
        "unknown": unknown,
        "pending": pending,
        "hit_rate_percent": hit_rate,
        "latest_signal": _decorate_signal(latest) if latest is not None else None,
    }


def _price_ticks_count(
    session: dict[str, Any] | None = None,
    asset: Any = None,
) -> int:
    _ensure_signal_db()
    session = session or {}
    started_at = _session_started_at(session)
    session_id = _session_id(session)
    asset_text = _as_text(asset)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT created_at, asset, metadata_json FROM price_ticks"
        ).fetchall()

    count = 0
    for row in rows:
        if session_id:
            metadata_session_id = _metadata_session_id(row["metadata_json"])
            if metadata_session_id and metadata_session_id != session_id:
                continue
        if started_at is not None:
            row_dt = _parse_dt(row["created_at"])
            if row_dt is None or _dt_timestamp(row_dt) < _dt_timestamp(started_at):
                continue
        if _is_valid_asset(asset_text) and _as_text(row["asset"]).lower() != asset_text.lower():
            continue
        count += 1
    return count


def _average_history_interval_seconds(history: list[dict[str, Any]]) -> float | None:
    timestamps = [
        _dt_timestamp(parsed)
        for parsed in (_parse_dt(point.get("timestamp")) for point in history)
        if parsed is not None
    ]
    if len(timestamps) < 2:
        return None
    intervals = [
        max(0.0, timestamps[index] - timestamps[index - 1])
        for index in range(1, len(timestamps))
    ]
    return round(sum(intervals) / len(intervals), 3) if intervals else None


def _final_price_search_status(latest_signal: dict[str, Any] | None) -> str:
    if not latest_signal:
        return "NO_SIGNAL"

    status = str(latest_signal.get("status") or latest_signal.get("result") or "")
    if status in {"PENDING", WAITING_RESULT_STATUS}:
        remaining = latest_signal.get("remaining_seconds")
        if isinstance(remaining, (int, float)) and remaining > 0:
            return "WAITING_TARGET_TIME"
        return str(
            latest_signal.get("result_price_search_status")
            or WAITING_RESULT_STATUS
        )
    return str(
        latest_signal.get("result_price_search_status")
        or latest_signal.get("result")
        or status
        or "UNKNOWN"
    )


def _price_diagnostics(
    history: list[dict[str, Any]],
    signal_stats: dict[str, Any],
    *,
    session: dict[str, Any] | None = None,
    asset: Any = None,
) -> dict[str, Any]:
    latest = history[-1] if history else {}
    latest_dt = _parse_dt(latest.get("timestamp"))
    age = None
    if latest_dt is not None:
        age = int(max(0, _dt_timestamp(_now()) - _dt_timestamp(latest_dt)))

    latest_signal = signal_stats.get("latest_signal")
    return {
        "last_price_age_seconds": age,
        "history_count": len(history),
        "average_interval_seconds": _average_history_interval_seconds(history),
        "last_history_timestamp": latest.get("timestamp"),
        "price_ticks_count": _price_ticks_count(session=session, asset=asset),
        "final_price_search_status": _final_price_search_status(latest_signal),
        "waiting_result_count": int(signal_stats.get("pending") or 0),
    }


def _reader_running() -> bool:
    return _reader_process is not None and _reader_process.poll() is None


def _clear_reader_process_cache() -> None:
    global _reader_process_cache_at, _reader_process_cache
    _reader_process_cache_at = 0.0
    _reader_process_cache = []


def _reader_interval_from_processes(processes: list[dict[str, Any]]) -> int:
    for process in processes:
        match = re.search(r"--loop-interval\s+(\d+)", str(process.get("command_line") or ""))
        if match:
            return max(1, int(match.group(1)))
    return DEFAULT_READER_INTERVAL_SECONDS


def _active_reader_processes(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    global _reader_process_cache_at, _reader_process_cache

    now = time.time()
    if not force_refresh and now - _reader_process_cache_at < 2:
        return _reader_process_cache

    if os.name != "nt":
        _reader_process_cache_at = now
        _reader_process_cache = []
        return []

    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { ($_.Name -like 'python*' -or $_.Name -like 'py*') -and "
        "$_.CommandLine -like '*predixai.main*' -and "
        "$_.CommandLine -like '*--live-loop*' -and "
        "$_.CommandLine -like '*--price-only*' } | "
        "ForEach-Object { \"$($_.ProcessId)|$($_.ParentProcessId)|$($_.ExecutablePath)|$($_.CommandLine)\" }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        _reader_process_cache_at = now
        _reader_process_cache = []
        return []

    processes: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        if "|" not in line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 2:
            pid_text, command_line = parts
            parent_pid_text = ""
            executable = ""
        elif len(parts) == 3:
            pid_text, parent_pid_text, command_line = parts
            executable = ""
        elif len(parts) == 4:
            pid_text, parent_pid_text, executable, command_line = parts
        else:
            continue
        try:
            pid = int(pid_text.strip())
        except ValueError:
            continue
        try:
            parent_pid = int(parent_pid_text.strip()) if parent_pid_text.strip() else None
        except ValueError:
            parent_pid = None
        processes.append(
            {
                "pid": pid,
                "parent_pid": parent_pid,
                "executable": executable.strip(),
                "command_line": command_line.strip(),
            }
        )

    matching_pids = {int(process["pid"]) for process in processes if process.get("pid")}
    processes = [
        process
        for process in processes
        if process.get("parent_pid") not in matching_pids
    ]

    _reader_process_cache_at = now
    _reader_process_cache = processes
    return processes


def _reader_warning(processes: list[dict[str, Any]]) -> str:
    if len(processes) <= 1:
        return ""
    return f"Aviso: {len(processes)} leitores live-loop ativos detectados."


def _start_reader(interval: Any) -> dict[str, Any]:
    with _reader_start_lock:
        return _start_reader_locked(interval)


def _start_reader_locked(interval: Any) -> dict[str, Any]:
    global _reader_interval, _reader_process

    try:
        interval = max(1, int(interval))
    except (TypeError, ValueError):
        interval = DEFAULT_READER_INTERVAL_SECONDS

    if _reader_running():
        active_readers = _active_reader_processes(force_refresh=True)
        return {
            "status": "ALREADY_RUNNING",
            "interval": _reader_interval,
            "pid": _reader_process.pid if _reader_process else None,
            "observer_only": True,
            "active_reader_count": max(1, len(active_readers)),
            "active_readers": active_readers,
        }

    active_readers = _active_reader_processes(force_refresh=True)
    if active_readers:
        _reader_interval = _reader_interval_from_processes(active_readers)
        return {
            "status": "ALREADY_RUNNING",
            "interval": _reader_interval,
            "observer_only": True,
            "warning": _reader_warning(active_readers) or "Leitor live-loop ja esta ativo.",
            "active_reader_count": len(active_readers),
            "active_readers": active_readers,
        }

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable,
        "-m",
        "predixai.main",
        "--live-loop",
        "--price-only",
        "--loop-count",
        "9999",
        "--loop-interval",
        str(interval),
    ]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    reader_log_path = RUNTIME_DIR / "mobile_reader.log"
    reader_log = None
    try:
        reader_log = reader_log_path.open("ab")
        _reader_process = subprocess.Popen(
            cmd,
            cwd=str(ROOT_DIR),
            env=env,
            stdout=reader_log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    except Exception as exc:
        _reader_process = None
        _reader_interval = None
        _clear_reader_process_cache()
        return {
            "status": "START_FAILED",
            "message": "Falha ao iniciar leitor live-loop.",
            "error": str(exc),
            "interval": interval,
            "observer_only": True,
            "active_reader_count": 0,
            "log_path": str(reader_log_path),
        }
    finally:
        if reader_log is not None and not reader_log.closed:
            reader_log.close()

    time.sleep(0.25)
    if _reader_process.poll() is not None:
        returncode = _reader_process.returncode
        _reader_process = None
        _reader_interval = None
        _clear_reader_process_cache()
        return {
            "status": "START_FAILED",
            "message": "Leitor live-loop encerrou logo apos iniciar.",
            "returncode": returncode,
            "interval": interval,
            "observer_only": True,
            "active_reader_count": 0,
            "log_path": str(reader_log_path),
        }

    _reader_interval = interval
    _clear_reader_process_cache()
    return {
        "status": "STARTED",
        "interval": interval,
        "pid": _reader_process.pid,
        "observer_only": True,
        "active_reader_count": 1,
        "log_path": str(reader_log_path),
    }


def _stop_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        subprocess.run(
            ["kill", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _stop_reader() -> dict[str, Any]:
    global _reader_interval, _reader_process

    active_readers = _active_reader_processes(force_refresh=True)
    pids = {int(process["pid"]) for process in active_readers if process.get("pid")}
    if _reader_running() and _reader_process is not None:
        pids.add(int(_reader_process.pid))

    if not pids:
        _reader_process = None
        _reader_interval = None
        _clear_reader_process_cache()
        return {"status": "NOT_RUNNING", "observer_only": True}

    for pid in sorted(pids):
        _stop_process_tree(pid)
    _reader_process = None
    _reader_interval = None
    _clear_reader_process_cache()
    return {
        "status": "STOPPED",
        "pids": sorted(pids),
        "stopped_count": len(pids),
        "observer_only": True,
    }


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
    expiration_seconds: int = DEFAULT_EXPIRATION_SECONDS,
) -> dict[str, Any]:
    expiration_seconds = _normalize_expiration_seconds(expiration_seconds)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    last = _read_json(LAST_READING_PATH, {})
    if not isinstance(last, dict):
        last = {}
    mobile_session = _read_mobile_session()
    scoped_last = last if _event_in_session(last, mobile_session) else {}
    raw_history = _collect_price_history(limit=None)
    session_history = _filter_history_scope(raw_history, mobile_session)
    rejected = _read_json(REJECTED_READINGS_PATH, [])
    if not isinstance(rejected, list):
        rejected = []
    rejected = [
        item
        for item in rejected
        if isinstance(item, dict) and _event_in_session(item, mobile_session)
    ]

    reader_processes = _active_reader_processes()
    running = _reader_running() or bool(reader_processes)
    effective_reader_interval = _reader_interval or _reader_interval_from_processes(reader_processes)
    duplicate_reader_warning = _reader_warning(reader_processes)

    latest_session_history = session_history[-1] if session_history else {}
    last_asset = _as_text(_extract_value(scoped_last, {"asset", "symbol", "active", "instrument"}))
    history_asset = _as_text(latest_session_history.get("asset"))
    session_asset = _as_text(mobile_session.get("asset"))
    text_asset = _asset_from_text(scoped_last)
    asset = next(
        (
            candidate
            for candidate in (last_asset, session_asset, history_asset, text_asset)
            if _is_valid_asset(candidate)
        ),
        "UNKNOWN",
    )
    if _is_valid_asset(asset):
        _update_mobile_session_asset(mobile_session, asset)
        full_history = _filter_history_scope(raw_history, mobile_session, asset=asset)
    else:
        full_history = session_history
    history = full_history[-SESSION_HISTORY_LIMIT:]
    latest_history = history[-1] if history else latest_session_history

    _check_pending_signals(full_history)
    support, resistance = _support_resistance(history)

    price = None
    last_price = _parse_float(_extract_value(scoped_last, {"price_value", "price", "current_price", "last_price"}))
    if _is_valid_price(last_price, last_asset):
        price = last_price
        asset = last_asset
    else:
        history_price = _parse_float(latest_history.get("price_value"))
        if _is_valid_price(history_price, history_asset):
            price = history_price
            asset = history_asset

    computed = _compute_signal(history)
    raw_signal = _extract_value(
        scoped_last,
        {"signal", "instruction", "robot_instruction", "decision", "action"},
    )
    signal = _normalize_signal(raw_signal) if raw_signal else computed["signal"]
    if signal not in {"AGUARDAR", "OBSERVAR ALTA", "OBSERVAR BAIXA"}:
        signal = computed["signal"]

    direction = _as_text(_extract_value(scoped_last, {"direction", "trend", "market_direction"}))
    if not direction:
        direction = computed["direction"]

    confidence = _parse_float(_extract_value(scoped_last, {"confidence", "confidence_pct", "score"}))
    if confidence is None:
        confidence = _parse_float(computed["confidence"])

    reason = (
        _as_text(_extract_value(scoped_last, {"reason", "message", "analysis_reason", "explanation"}))
        or computed["reason"]
    )

    last_status = _as_text(scoped_last.get("status")).upper()
    latest_rejected = _latest_rejection(rejected)
    rejection_reason = _as_text(_extract_value(latest_rejected, {"reason", "message", "status_reason"}))
    latest_rejection_status = _as_text(
        _extract_value(latest_rejected, {"status"})
    ).upper()
    latest_rejection_is_price_not_found = (
        latest_rejection_status == "PRICE_NOT_FOUND"
        or "price_not_found" in rejection_reason.lower()
        or "preco nao encontrado" in rejection_reason.lower()
        or "preço não encontrado" in rejection_reason.lower()
    )
    ignored_window = (
        last_status == "IGNORED_WINDOW"
        or (
            bool(last.get("capture_skipped"))
            and last_status == "IGNORED_WINDOW"
        )
        or (
            _latest_event_is_rejection(scoped_last, latest_rejected)
            and last_status != "PRICE_NOT_FOUND"
            and not latest_rejection_is_price_not_found
        )
    )
    valid_age = _file_age_seconds(PRICE_HISTORY_PATH) if history else None
    event_age = _file_age_seconds(LAST_READING_PATH) if scoped_last else None
    age = valid_age if valid_age is not None else event_age

    if ignored_window and running:
        status = "Rodando — aguardando preço"
        message = rejection_reason or reason or "Leitor ativo; aguardando a janela da corretora."
        signal = "AGUARDAR"
        confidence = 0
    elif running and price is None:
        status = "Rodando — aguardando preço"
        message = "Leitor ativo; aguardando primeiro preço válido."
    elif running and (valid_age is None or valid_age > max(4, effective_reader_interval * 3)):
        status = "Rodando — aguardando preço"
        message = "Leitor ativo; aguardando nova leitura de preço."
    elif running:
        status = "Rodando"
        message = "Leitor ativo. Acompanhe apenas em modo simulado."
    else:
        status = "Parado"
        if ignored_window:
            message = "Leitor parado. Última tentativa encontrou janela errada; dados abaixo usam o histórico válido."
        else:
            message = "Leitor parado. Sinais abaixo são históricos."

    if duplicate_reader_warning:
        message = f"{message} {duplicate_reader_warning}"

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
        "last_window_title": scoped_last.get("window_title") or (scoped_last.get("broker_window") or {}).get("title"),
        "expiration_seconds": expiration_seconds,
        "session_id": _session_id(mobile_session),
        "support": support,
        "resistance": resistance,
        "reader_warning": duplicate_reader_warning,
    }

    if status == "Rodando":
        _register_signal_if_needed(state, expiration_seconds=expiration_seconds)
    signals = _list_signals(session=mobile_session, asset=asset)
    signal_stats = _signal_stats(session=mobile_session, asset=asset)
    price_history = [
        {
            "timestamp": point.get("timestamp"),
            "asset": point.get("asset"),
            "price": point.get("price_value"),
            "price_value": point.get("price_value"),
        }
        for point in history
    ]

    host = host_for_url or _local_ip()
    return {
        "notice": OBSERVATION_NOTICE,
        "simulation_notice": SIMULATION_NOTICE,
        "reader_running": running,
        "reader_interval": effective_reader_interval,
        "active_reader_count": max(1, len(reader_processes)) if running else 0,
        "active_readers": reader_processes,
        "reader_warning": duplicate_reader_warning,
        "signal_analysis_interval": SIGNAL_ANALYSIS_INTERVAL_SECONDS,
        "expiration_seconds": expiration_seconds,
        "support": support,
        "resistance": resistance,
        "mobile_url": f"http://{host}:{port}/mobile",
        "state": state,
        "history": history,
        "price_history": price_history,
        "signals": signals,
        "signal_stats": signal_stats,
        "price_diagnostics": _price_diagnostics(
            full_history,
            signal_stats,
            session=mobile_session,
            asset=asset,
        ),
        "recent_rejections": rejected[-10:],
        "db_path": str(SIGNALS_DB_PATH),
        "mobile_session": mobile_session,
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


def _handle_get(
    path: str,
    host_header: str | None = None,
    query: dict[str, list[str]] | None = None,
) -> tuple[int, str, bytes]:
    query = query or {}
    if path in {"/", "/mobile"}:
        return 200, "text/html; charset=utf-8", MOBILE_HTML.encode("utf-8")
    if path == "/api/mobile/state":
        host = _host_from_header(host_header)
        port = _port_from_header(host_header)
        expiration_seconds = _normalize_expiration_seconds((query.get("expiration") or [DEFAULT_EXPIRATION_SECONDS])[0])
        return 200, "application/json; charset=utf-8", _json_bytes(
            _build_state(host_for_url=host, port=port, expiration_seconds=expiration_seconds)
        )
    return 404, "application/json; charset=utf-8", _json_bytes({"status": "NOT_FOUND"})


def _handle_post(
    path: str,
    query: dict[str, list[str]] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, str, bytes]:
    query = query or {}
    if path in SIMULATED_START_ROUTES:
        result = _start_simulated_mobile_session(payload)
        status_code = 200 if result.get("ok") else 400
        return status_code, "application/json; charset=utf-8", _json_bytes(result)
    if path == "/api/mobile/start":
        result = _start_simulated_mobile_session(payload)
        result["compatibility_route"] = "/api/mobile/start"
        result["legacy_live_loop_disabled"] = True
        status_code = 200 if result.get("ok") else 400
        return status_code, "application/json; charset=utf-8", _json_bytes(result)
    if path == "/api/mobile/stop":
        return 200, "application/json; charset=utf-8", _json_bytes(_stop_reader())
    if path == "/api/mobile/reset-session":
        dry_run = str((query.get("dry_run") or ["0"])[0]).lower() in {"1", "true", "yes"}
        try:
            result = _reset_mobile_session(dry_run=dry_run)
            return 200, "application/json; charset=utf-8", _json_bytes(result)
        except Exception as exc:
            return 500, "application/json; charset=utf-8", _json_bytes(
                {
                    "status": "RESET_FAILED",
                    "message": "Falha ao criar backup/limpar sessão.",
                    "error": str(exc),
                    "observer_only": True,
                }
            )
    return 404, "application/json; charset=utf-8", _json_bytes({"status": "NOT_FOUND"})


class MobileRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        status, content_type, body = _handle_get(
            parsed.path,
            host_header=self.headers.get("Host"),
            query=parse_qs(parsed.query),
        )
        self._send(status, content_type, body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        payload: dict[str, Any] | None = None
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        if length > 0:
            try:
                decoded = self.rfile.read(length).decode("utf-8")
                loaded = json.loads(decoded) if decoded.strip() else {}
                if isinstance(loaded, dict):
                    payload = loaded
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
        status, content_type, body = _handle_post(
            parsed.path,
            query=parse_qs(parsed.query),
            payload=payload,
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



# PTP-113B.2.3 — Tela inicial e contrato visual do sinal
SESSION_SETUP_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PredixAI BR — Iniciar Sessão</title>
<style>
body{margin:0;background:#07111f;color:#eaf4ff;font-family:Arial,sans-serif}
.wrap{max-width:540px;margin:0 auto;padding:22px}
.card{background:#0d1c31;border:1px solid #1f3c5c;border-radius:18px;padding:20px;box-shadow:0 0 22px #0008}
h1{font-size:24px;margin:0 0 8px;color:#66d9ff}
p{color:#b8c7d9;line-height:1.45}
label{display:block;margin-top:14px;font-weight:bold}
select,input{width:100%;padding:12px;border-radius:10px;border:1px solid #2c5278;background:#081625;color:#fff;font-size:16px;box-sizing:border-box}
button{width:100%;margin-top:22px;padding:15px;border:0;border-radius:12px;background:#d8aa3a;color:#08111f;font-weight:bold;font-size:17px}
.note{margin-top:14px;font-size:13px;color:#90a7bd;line-height:1.4}
.badge{display:inline-block;background:#12324f;border:1px solid #2b6e9f;color:#9de6ff;border-radius:999px;padding:6px 10px;font-size:12px;margin-bottom:10px}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<div class="badge">MODO 100% SIMULADO</div>
<h1>PredixAI Trader</h1>
<p>Configure a sessão antes de abrir o painel mobile de observação e sinais.</p>

<label>Estratégia</label>
<select id="strategy">
<option value="scalper">Scalper</option>
<option value="day_trade">Day Trade</option>
</select>

<label>Perfil de risco</label>
<select id="risk">
<option value="conservador">Conservador</option>
<option value="moderado">Moderado</option>
<option value="agressivo">Agressivo</option>
</select>

<label>Banca simulada</label>
<input id="bankroll" type="number" value="100" min="1">

<label>Valor da entrada simulada</label>
<input id="entry_amount" type="number" value="5" min="1">

<label>Tempo de expiração</label>
<select id="expiration">
<option value="60">60 segundos</option>
<option value="300">5 minutos</option>
<option value="900">15 minutos</option>
</select>

<button onclick="startSession()">Iniciar sessão simulada</button>

<div class="note">
Nenhuma corretora real será aberta. Nenhum login, saldo real, clique automático ou ordem real será usado.
</div>
</div>
</div>

<script>
async function startSession(){
  const payload = {
    strategy: document.getElementById("strategy").value,
    risk_profile: document.getElementById("risk").value,
    bankroll: Number(document.getElementById("bankroll").value),
    entry_amount: Number(document.getElementById("entry_amount").value),
    expiration_seconds: Number(document.getElementById("expiration").value)
  };

  const res = await fetch("/mobile/session/start", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload)
  });

  if(!res.ok){
    alert("Falha ao iniciar sessão simulada.");
    return;
  }

  window.location.href = "/mobile";
}
</script>
</body>
</html>
"""


def predixai_visual_signal_contract():
    return {
        "required_visual_fields": [
            "ativo",
            "direcao",
            "horario_entrada",
            "preco_referencia",
            "tempo_expiracao",
            "alerta_cancelamento",
            "explicacao",
            "confianca",
            "status",
        ],
        "example": {
            "ativo": "Cafeina Index",
            "direcao": "COMPRA / VENDA / AGUARDAR",
            "horario_entrada": "HH:MM:SS",
            "preco_referencia": "preço ou zona de entrada",
            "tempo_expiracao": "60 segundos / 5 minutos / 15 minutos",
            "alerta_cancelamento": "Cancelar se o preço fugir da zona antes do horário de entrada.",
            "explicacao": "Motivo técnico da sugestão conforme estratégia escolhida.",
            "confianca": "0-100%",
            "status": "AGUARDANDO HORÁRIO DE ENTRADA",
        },
    }


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


    @app.route("/session/setup")
    def session_setup():  # type: ignore[no-untyped-def]
        return SESSION_SETUP_HTML

    @app.route("/api/mobile/signal/contract")
    def mobile_signal_contract():  # type: ignore[no-untyped-def]
        return jsonify(predixai_visual_signal_contract())

    @app.route("/mobile")
    def mobile():  # type: ignore[no-untyped-def]
        return MOBILE_HTML

    @app.route("/api/mobile/state")
    def mobile_state():  # type: ignore[no-untyped-def]
        host = _host_from_header(request.host)
        port = _port_from_header(request.host)
        expiration_seconds = _normalize_expiration_seconds(request.args.get("expiration"))
        return jsonify(
            _build_state(
                host_for_url=host,
                port=port,
                expiration_seconds=expiration_seconds,
            )
        )

    @app.route("/api/mobile/start", methods=["POST"])
    def mobile_start():  # type: ignore[no-untyped-def]
        payload = request.get_json(silent=True) or {}
        result = _start_simulated_mobile_session(payload if isinstance(payload, dict) else {})
        result["compatibility_route"] = "/api/mobile/start"
        result["legacy_live_loop_disabled"] = True
        status_code = 200 if result.get("ok") else 400
        return jsonify(result), status_code

    @app.route("/mobile/session/start", methods=["POST"])
    @app.route("/api/mobile/simulated-session/start", methods=["POST"])
    def mobile_simulated_session_start():  # type: ignore[no-untyped-def]
        payload = request.get_json(silent=True) or {}
        result = _start_simulated_mobile_session(payload if isinstance(payload, dict) else {})
        status_code = 200 if result.get("ok") else 400
        return jsonify(result), status_code

    @app.route("/api/mobile/stop", methods=["POST"])
    def mobile_stop():  # type: ignore[no-untyped-def]
        return jsonify(_stop_reader())

    @app.route("/api/mobile/reset-session", methods=["POST"])
    def mobile_reset_session():  # type: ignore[no-untyped-def]
        dry_run = str(request.args.get("dry_run", "0")).lower() in {"1", "true", "yes"}
        try:
            return jsonify(_reset_mobile_session(dry_run=dry_run))
        except Exception as exc:
            return jsonify(
                {
                    "status": "RESET_FAILED",
                    "message": "Falha ao criar backup/limpar sessão.",
                    "error": str(exc),
                    "observer_only": True,
                }
            ), 500

    # BEGIN PTP-113B.3.1A COMPLETE SESSION CONTRACT
    def _ptp113b31a_strategy_catalog():
        return {
            "support_resistance": {
                "label": "Suporte e resistência",
                "signals_5m_scalper": 1,
                "signals_1h_scalper": 8,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 3,
                "risk": "médio",
                "description": "Busca zonas de suporte/resistência e aguarda reação do preço.",
            },
            "candle_reversal": {
                "label": "Reversão de vela",
                "signals_5m_scalper": 1,
                "signals_1h_scalper": 10,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 4,
                "risk": "médio/alto",
                "description": "Busca sinais de reversão após movimento curto ou esticado.",
            },
            "breakout": {
                "label": "Rompimento",
                "signals_5m_scalper": 1,
                "signals_1h_scalper": 7,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 3,
                "risk": "alto",
                "description": "Busca rompimento de zona relevante com confirmação mínima.",
            },
            "moving_average_trend": {
                "label": "Tendência por médias",
                "signals_5m_scalper": 0,
                "signals_1h_scalper": 6,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 2,
                "risk": "médio",
                "description": "Usa direção das médias para filtrar compra, venda ou aguardar.",
            },
            "pullback": {
                "label": "Pullback",
                "signals_5m_scalper": 1,
                "signals_1h_scalper": 6,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 2,
                "risk": "médio",
                "description": "Aguarda retorno do preço para uma zona antes de sugerir entrada.",
            },
            "simple_confluence": {
                "label": "Confluência simples",
                "signals_5m_scalper": 1,
                "signals_1h_scalper": 5,
                "signals_5m_day_trade": 0,
                "signals_1h_day_trade": 2,
                "risk": "baixo/médio",
                "description": "Só libera sinal quando múltiplos critérios técnicos concordam.",
            },
        }

    def _ptp113b31a_float(value, default):
        try:
            parsed = float(str(value).replace(",", "."))
            return parsed if parsed >= 0 else default
        except Exception:
            return default

    def _ptp113b31a_int(value, default):
        try:
            parsed = int(float(str(value).replace(",", ".")))
            return parsed if parsed > 0 else default
        except Exception:
            return default

    def _ptp113b31a_build_contract(form=None):
        form = form or {}
        catalog = _ptp113b31a_strategy_catalog()

        operational_mode = str(form.get("operational_mode") or form.get("mode") or "scalper").strip()
        if operational_mode not in {"scalper", "day_trade"}:
            operational_mode = "scalper"

        strategy_key = str(form.get("strategy_key") or form.get("strategy") or "simple_confluence").strip()
        if strategy_key not in catalog:
            strategy_key = "simple_confluence"

        initial_bankroll = _ptp113b31a_float(form.get("initial_bankroll") or form.get("bankroll"), 100.0)
        current_bankroll = _ptp113b31a_float(form.get("current_bankroll"), initial_bankroll)
        current_entry = _ptp113b31a_float(form.get("current_entry") or form.get("entry_amount"), 5.0)
        expiration_seconds = _ptp113b31a_int(form.get("expiration_seconds"), 60)
        risk_profile = str(form.get("risk_profile") or "conservador").strip() or "conservador"

        meta = catalog[strategy_key]
        if operational_mode == "scalper":
            signals_5m = meta["signals_5m_scalper"]
            signals_1h = meta["signals_1h_scalper"]
            mode_label = "Scalper"
            mode_description = "Sessão curta, com foco em sinais rápidos e controle rígido."
        else:
            signals_5m = meta["signals_5m_day_trade"]
            signals_1h = meta["signals_1h_day_trade"]
            mode_label = "Day Trade"
            mode_description = "Sessão mais lenta, com menos sinais e maior seletividade."

        max_entries_by_bankroll = int(current_bankroll // current_entry) if current_entry > 0 else 0
        estimated_consumption_1h = round(min(signals_1h, max_entries_by_bankroll) * current_entry, 2)
        estimated_consumption_percent = round((estimated_consumption_1h / current_bankroll) * 100, 2) if current_bankroll else 0.0

        return {
            "simulation_only": True,
            "orders_enabled": False,
            "real_money_enabled": False,
            "auto_click_enabled": False,
            "broker_login_enabled": False,
            "credentials_allowed": False,
            "operational_mode": {
                "key": operational_mode,
                "label": mode_label,
                "description": mode_description,
            },
            "strategy": {
                "key": strategy_key,
                "label": meta["label"],
                "risk": meta["risk"],
                "description": meta["description"],
            },
            "bankroll": {
                "currency": "BRL",
                "initial_bankroll": initial_bankroll,
                "current_bankroll": current_bankroll,
                "current_entry": current_entry,
                "profit_loss": round(current_bankroll - initial_bankroll, 2),
                "profit_loss_percent": round(((current_bankroll - initial_bankroll) / initial_bankroll) * 100, 2) if initial_bankroll else 0.0,
            },
            "risk": {
                "profile": risk_profile,
                "entry_percent_of_bankroll": round((current_entry / current_bankroll) * 100, 2) if current_bankroll else 0.0,
                "estimated_consumption_1h": estimated_consumption_1h,
                "estimated_consumption_percent_1h": estimated_consumption_percent,
            },
            "expiration": {
                "seconds": expiration_seconds,
                "label": f"{expiration_seconds} segundos" if expiration_seconds < 60 else f"{int(expiration_seconds/60)} minuto(s)",
            },
            "preview": {
                "estimated_signals_5m": signals_5m,
                "estimated_signals_1h": signals_1h,
                "session_classification": "alta frequência" if signals_1h >= 8 else "seletiva",
                "recommendation": "Operar somente em modo simulado e cancelar se o preço fugir da zona.",
                "general_safety_rule": "A condição específica de cancelamento será exibida junto do sinal gerado.",
            "cancel_alert": "Cancelamento específico será calculado no sinal conforme ativo, preço, horário e estratégia.",
            },
            "required_visual_fields": [
                "ativo",
                "direcao",
                "horario_entrada",
                "preco_referencia",
                "tempo_expiracao",
                "alerta_cancelamento",
                "explicacao",
                "confianca",
                "status",
                "modo_operacional",
                "estrategia_geradora",
                "banca_simulada",
                "saldo_atual",
                "entrada_simulada",
                "risco",
                "estimativa_sinais_5m",
                "estimativa_sinais_1h",
            ],
            "security": {
                "simulation_only": True,
                "orders_enabled": False,
                "real_money_enabled": False,
                "auto_click_enabled": False,
                "broker_login_enabled": False,
                "credentials_allowed": False,
            },
        }

    def _ptp113b31a_session_setup_override():
        from flask import request, redirect, Response
        contract = _ptp113b31a_build_contract(request.form if request.method == "POST" else {})
        app.config["PTP113B31A_SESSION_CONTRACT"] = contract

        if request.method == "POST":
            return redirect("/mobile")

        html = f"""<!doctype html>
    <html lang="pt-BR">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PredixAI BR — Iniciar Sessão Simulada</title>
    <style>
    body{{margin:0;background:#07111f;color:#eaf4ff;font-family:Arial,sans-serif}}
    .wrap{{max-width:620px;margin:0 auto;padding:22px}}
    .card{{background:#0d1c31;border:1px solid #1f3c5c;border-radius:18px;padding:20px;box-shadow:0 0 22px #0008}}
    h1{{font-size:24px;margin:0 0 8px;color:#66d9ff}}
    h2{{font-size:17px;margin:22px 0 8px;color:#d8aa3a}}
    p{{color:#b8c7d9;line-height:1.45}}
    label{{display:block;margin-top:14px;font-weight:bold}}
    select,input{{width:100%;padding:12px;border-radius:10px;border:1px solid #2c5278;background:#081625;color:#fff;font-size:16px;box-sizing:border-box}}
    button{{width:100%;margin-top:22px;padding:15px;border:0;border-radius:12px;background:#d8aa3a;color:#08111f;font-weight:bold;font-size:17px}}
    .badge{{display:inline-block;background:#12324f;border:1px solid #2b6e9f;color:#9de6ff;border-radius:999px;padding:6px 10px;font-size:12px;margin-bottom:10px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .box{{background:#081625;border:1px solid #1f3c5c;border-radius:12px;padding:12px;margin-top:10px}}
    .k{{font-size:12px;color:#8fa6bd}}
    .v{{font-size:18px;font-weight:bold;color:#fff;margin-top:4px}}
    .note{{margin-top:14px;font-size:13px;color:#90a7bd;line-height:1.4}}
    .warn{{border-color:#d8aa3a;color:#ffe4a0}}
    </style>
    </head>
    <body>
    <div class="wrap">
    <div class="card">
    <div class="badge">MODO 100% SIMULADO</div>
    <h1>PredixAI Trader — Configurar Sessão</h1>
    <p>Configure o contrato operacional antes de abrir o painel mobile. Nenhuma ordem real, clique automático, login ou saldo real será usado.</p>

    <form method="post">
    <h2>1. Modo operacional</h2>
    <label>Modo</label>
    <select name="operational_mode" id="operational_mode" onchange="updatePreview()">
    <option value="scalper">Scalper — sinais rápidos</option>
    <option value="day_trade">Day Trade — sinais mais seletivos</option>
    </select>

    <h2>2. Estratégia geradora do sinal</h2>
    <label>Estratégia</label>
    <select name="strategy_key" id="strategy_key" onchange="updatePreview()">
    <option value="support_resistance">Suporte e resistência</option>
    <option value="candle_reversal">Reversão de vela</option>
    <option value="breakout">Rompimento</option>
    <option value="moving_average_trend">Tendência por médias</option>
    <option value="pullback">Pullback</option>
    <option value="simple_confluence" selected>Confluência simples</option>
    </select>

    <h2>3. Banca simulada e risco</h2>
    <label>Banca simulada inicial</label>
    <input name="initial_bankroll" id="initial_bankroll" type="number" step="0.01" value="{contract['bankroll']['initial_bankroll']}" oninput="updatePreview()">

    <label>Valor da entrada simulada</label>
    <input name="current_entry" id="current_entry" type="number" step="0.01" value="{contract['bankroll']['current_entry']}" oninput="updatePreview()">

    <label>Expiração</label>
    <select name="expiration_seconds" id="expiration_seconds">
    <option value="30">30 segundos</option>
    <option value="60" selected>60 segundos</option>
    <option value="300">5 minutos</option>
    <option value="900">15 minutos</option>
    </select>

    <label>Perfil de risco</label>
    <select name="risk_profile" id="risk_profile">
    <option value="conservador" selected>Conservador</option>
    <option value="moderado">Moderado</option>
    <option value="agressivo_simulado">Agressivo apenas simulado</option>
    </select>

    <h2>4. Prévia operacional</h2>
    <div class="grid">
    <div class="box"><div class="k">Estimativa em 5 min</div><div class="v" id="signals5">1 sinal</div></div>
    <div class="box"><div class="k">Estimativa em 1 hora</div><div class="v" id="signals1h">5 sinais</div></div>
    <div class="box"><div class="k">Risco da estratégia</div><div class="v" id="riskBox">baixo/médio</div></div>
    <div class="box"><div class="k">Consumo estimado 1h</div><div class="v" id="consumption">R$ 25,00</div></div>
    </div>

    <div class="box warn">
    <div class="k">Alerta de cancelamento</div>
    <div class="note" id="cancelAlert">Cancelar se o preço fugir da zona antes do horário de entrada.</div>
    </div>

    <button type="submit">Iniciar sessão simulada</button>
    </form>

    <div class="note">
    Contrato: mobile-first, observador visual, motor lógico programado, saldo simulado e segurança travada.
    </div>
    </div>
    </div>

    <script>
    const catalog = {{
      support_resistance: {{label:"Suporte e resistência", scalper5:1, scalper1h:8, day5:0, day1h:3, risk:"médio"}},
      candle_reversal: {{label:"Reversão de vela", scalper5:1, scalper1h:10, day5:0, day1h:4, risk:"médio/alto"}},
      breakout: {{label:"Rompimento", scalper5:1, scalper1h:7, day5:0, day1h:3, risk:"alto"}},
      moving_average_trend: {{label:"Tendência por médias", scalper5:0, scalper1h:6, day5:0, day1h:2, risk:"médio"}},
      pullback: {{label:"Pullback", scalper5:1, scalper1h:6, day5:0, day1h:2, risk:"médio"}},
      simple_confluence: {{label:"Confluência simples", scalper5:1, scalper1h:5, day5:0, day1h:2, risk:"baixo/médio"}}
    }};
    function brl(v) {{ return "R$ " + Number(v || 0).toFixed(2).replace(".", ","); }}
    function updatePreview() {{
      const mode = document.getElementById("operational_mode").value;
      const strategy = document.getElementById("strategy_key").value;
      const bankroll = Number(document.getElementById("initial_bankroll").value || 0);
      const entry = Number(document.getElementById("current_entry").value || 0);
      const meta = catalog[strategy];
      const s5 = mode === "scalper" ? meta.scalper5 : meta.day5;
      const s1h = mode === "scalper" ? meta.scalper1h : meta.day1h;
      document.getElementById("signals5").innerText = s5 + (s5 === 1 ? " sinal" : " sinais");
      document.getElementById("signals1h").innerText = s1h + (s1h === 1 ? " sinal" : " sinais");
      document.getElementById("riskBox").innerText = meta.risk;
      document.getElementById("consumption").innerText = brl(Math.min(s1h * entry, bankroll));
    }}
    updatePreview();
    </script>
    </body>
    </html>"""
        return Response(html, mimetype="text/html; charset=utf-8")

    def _ptp113b31a_signal_contract_override():
        from flask import jsonify, request
        contract = app.config.get("PTP113B31A_SESSION_CONTRACT") or _ptp113b31a_build_contract(request.args)
        return jsonify({
        "available_strategies": _ptp113b31a_strategy_catalog(),
        "available_operational_modes": {
            "scalper": "Scalper — sinais rápidos",
            "day_trade": "Day Trade — sinais mais seletivos"
        },

            "version": "PTP-113B.3.1A",
            "status": "COMPLETE_SIMULATED_CONTRACT",
            "contract": contract,
            "required_visual_fields": contract["required_visual_fields"],
            "example": {
                "ativo": "LATAM Index",
                "direcao": "COMPRA / VENDA / AGUARDAR",
                "horario_entrada": "HH:MM:SS",
                "preco_referencia": "preço ou zona de entrada",
                "tempo_expiracao": contract["expiration"]["label"],
                "alerta_cancelamento": contract["preview"]["cancel_alert"],
                "explicacao": "Motivo técnico conforme modo operacional e estratégia geradora.",
                "confianca": "0-100%",
                "status": "AGUARDANDO HORÁRIO DE ENTRADA",
                "modo_operacional": contract["operational_mode"]["label"],
                "estrategia_geradora": contract["strategy"]["label"],
                "banca_simulada": contract["bankroll"]["initial_bankroll"],
                "saldo_atual": contract["bankroll"]["current_bankroll"],
                "entrada_simulada": contract["bankroll"]["current_entry"],
                "risco": contract["risk"],
                "estimativa_sinais_5m": contract["preview"]["estimated_signals_5m"],
                "estimativa_sinais_1h": contract["preview"]["estimated_signals_1h"],
            },
        })

    @app.after_request
    def _ptp113b31a_enrich_mobile_state(response):
        try:
            from flask import request
            import json as _json
            if request.path != "/api/mobile/state":
                return response

            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                return response

            contract = app.config.get("PTP113B31A_SESSION_CONTRACT") or _ptp113b31a_build_contract({})
            mobile_session = data.get("mobile_session")
            if not isinstance(mobile_session, dict):
                mobile_session = {}

            mobile_session["contract"] = contract
            mobile_session["operational_mode"] = contract["operational_mode"]
            mobile_session["strategy"] = contract["strategy"]
            mobile_session["simulated_bankroll"] = contract["bankroll"]
            mobile_session["risk"] = contract["risk"]
            mobile_session["preview"] = contract["preview"]

            data["mobile_session"] = mobile_session
            data["simulation_only"] = True
            data["orders_enabled"] = False
            data["real_money_enabled"] = False
            data["auto_click_enabled"] = False
            data["broker_login_enabled"] = False
            data["credentials_allowed"] = False
            data["ptp113b31a_contract_complete"] = True

            response.set_data(_json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        except Exception as exc:
            response.headers["X-PTP113B31A-State-Enrich-Error"] = str(exc)[:180]
        return response

    _found_session_setup = False
    _found_signal_contract = False
    for _rule in list(app.url_map.iter_rules()):
        if _rule.rule == "/session/setup":
            app.view_functions[_rule.endpoint] = _ptp113b31a_session_setup_override
            _found_session_setup = True
        if _rule.rule == "/api/mobile/signal/contract":
            app.view_functions[_rule.endpoint] = _ptp113b31a_signal_contract_override
            _found_signal_contract = True

    if not _found_session_setup:
        app.add_url_rule(
            "/session/setup",
            "ptp113b31a_session_setup",
            _ptp113b31a_session_setup_override,
            methods=["GET", "POST"],
        )

    if not _found_signal_contract:
        app.add_url_rule(
            "/api/mobile/signal/contract",
            "ptp113b31a_signal_contract",
            _ptp113b31a_signal_contract_override,
            methods=["GET"],
        )

    # BEGIN PTP-113B.3.1A.3 POST SESSION SETUP FIX
    _ptp113b31a_has_post_session_setup = False
    for _rule in list(app.url_map.iter_rules()):
        if _rule.rule == "/session/setup" and "POST" in _rule.methods:
            _ptp113b31a_has_post_session_setup = True

    if not _ptp113b31a_has_post_session_setup:
        app.add_url_rule(
            "/session/setup",
            "ptp113b31a_session_setup_post",
            _ptp113b31a_session_setup_override,
            methods=["POST"],
        )
    # END PTP-113B.3.1A.3 POST SESSION SETUP FIX

    # BEGIN PTP-113B.3.1A.4.1 PROFIT TARGET OVERRIDE
    def _ptp113b31a41_build_contract(form=None):
        form = form or {}
        contract = _ptp113b31a_build_contract(form)

        initial_bankroll = _ptp113b31a_float(form.get("initial_bankroll") or form.get("bankroll"), 100.0)
        current_bankroll = _ptp113b31a_float(form.get("current_bankroll"), initial_bankroll)
        desired_profit = _ptp113b31a_float(
            form.get("desired_profit") or form.get("session_profit_target") or form.get("profit_target"),
            25.0,
        )

        contract["profit_target"] = {
            "desired_profit": desired_profit,
            "target_bankroll": round(current_bankroll + desired_profit, 2),
            "target_profit_percent": round((desired_profit / current_bankroll) * 100, 2) if current_bankroll else 0.0,
            "label": f"R$ {desired_profit:.2f}",
            "note": "Meta de lucro apenas simulada para esta sessão.",
        }

        contract.setdefault("preview", {})
        contract["preview"]["general_safety_rule"] = "O cancelamento específico será exibido junto do sinal gerado."
        contract["preview"]["cancel_alert"] = "Cancelamento específico será calculado no sinal conforme ativo, preço, horário e estratégia."

        fields = contract.setdefault("required_visual_fields", [])
        for item in [
            "lucro_desejado_sessao",
            "saldo_alvo_sessao",
            "cancelamento_especifico_no_sinal",
        ]:
            if item not in fields:
                fields.append(item)

        return contract

    def _ptp113b31a41_session_setup_override():
        from flask import request, redirect, Response

        if request.method == "POST":
            contract = _ptp113b31a41_build_contract(request.form)
            app.config["PTP113B31A_SESSION_CONTRACT"] = contract
            return redirect("/mobile")

        contract = _ptp113b31a41_build_contract({})
        app.config["PTP113B31A_SESSION_CONTRACT"] = contract

        html = """<!doctype html>
    <html lang="pt-BR">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PredixAI BR — Iniciar Sessão Simulada</title>
    <style>
    body{margin:0;background:#07111f;color:#eaf4ff;font-family:Arial,sans-serif}
    .wrap{max-width:620px;margin:0 auto;padding:22px}
    .card{background:#0d1c31;border:1px solid #1f3c5c;border-radius:18px;padding:20px;box-shadow:0 0 22px #0008}
    h1{font-size:24px;margin:0 0 8px;color:#66d9ff}
    h2{font-size:17px;margin:22px 0 8px;color:#d8aa3a}
    p{color:#b8c7d9;line-height:1.45}
    label{display:block;margin-top:14px;font-weight:bold}
    select,input{width:100%;padding:12px;border-radius:10px;border:1px solid #2c5278;background:#081625;color:#fff;font-size:16px;box-sizing:border-box}
    button{width:100%;margin-top:22px;padding:15px;border:0;border-radius:12px;background:#d8aa3a;color:#08111f;font-weight:bold;font-size:17px}
    .badge{display:inline-block;background:#12324f;border:1px solid #2b6e9f;color:#9de6ff;border-radius:999px;padding:6px 10px;font-size:12px;margin-bottom:10px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .box{background:#081625;border:1px solid #1f3c5c;border-radius:12px;padding:12px;margin-top:10px}
    .k{font-size:12px;color:#8fa6bd}
    .v{font-size:18px;font-weight:bold;color:#fff;margin-top:4px}
    .note{margin-top:14px;font-size:13px;color:#90a7bd;line-height:1.4}
    .warn{border-color:#d8aa3a;color:#ffe4a0}
    </style>
    </head>
    <body>
    <div class="wrap">
    <div class="card">
    <div class="badge">MODO 100% SIMULADO</div>
    <h1>PredixAI Trader — Configurar Sessão</h1>
    <p>Configure o contrato operacional antes de abrir o painel mobile. Nenhuma ordem real, clique automático, login ou saldo real será usado.</p>

    <form method="post">
    <h2>1. Modo operacional</h2>
    <label>Modo</label>
    <select name="operational_mode" id="operational_mode" onchange="updatePreview()">
    <option value="scalper">Scalper — sinais rápidos</option>
    <option value="day_trade">Day Trade — sinais mais seletivos</option>
    </select>

    <h2>2. Estratégia geradora do sinal</h2>
    <label>Estratégia</label>
    <select name="strategy_key" id="strategy_key" onchange="updatePreview()">
    <option value="support_resistance">Suporte e resistência</option>
    <option value="candle_reversal">Reversão de vela</option>
    <option value="breakout">Rompimento</option>
    <option value="moving_average_trend">Tendência por médias</option>
    <option value="pullback">Pullback</option>
    <option value="simple_confluence" selected>Confluência simples</option>
    </select>

    <h2>3. Banca simulada, meta e risco</h2>
    <label>Banca simulada inicial</label>
    <input name="initial_bankroll" id="initial_bankroll" type="number" step="0.01" value="100" oninput="updatePreview()">

    <label>Valor da entrada simulada</label>
    <input name="current_entry" id="current_entry" type="number" step="0.01" value="5" oninput="updatePreview()">

    <label>Lucro desejado da sessão</label>
    <input name="desired_profit" id="desired_profit" type="number" step="0.01" value="25" oninput="updatePreview()">

    <label>Expiração</label>
    <select name="expiration_seconds" id="expiration_seconds">
    <option value="30">30 segundos</option>
    <option value="60" selected>60 segundos</option>
    <option value="300">5 minutos</option>
    <option value="900">15 minutos</option>
    </select>

    <label>Perfil de risco</label>
    <select name="risk_profile" id="risk_profile">
    <option value="conservador" selected>Conservador</option>
    <option value="moderado">Moderado</option>
    <option value="agressivo_simulado">Agressivo apenas simulado</option>
    </select>

    <h2>4. Prévia operacional</h2>
    <div class="grid">
    <div class="box"><div class="k">Estimativa em 5 min</div><div class="v" id="signals5">1 sinal</div></div>
    <div class="box"><div class="k">Estimativa em 1 hora</div><div class="v" id="signals1h">5 sinais</div></div>
    <div class="box"><div class="k">Risco da estratégia</div><div class="v" id="riskBox">baixo/médio</div></div>
    <div class="box"><div class="k">Consumo estimado 1h</div><div class="v" id="consumption">R$ 25,00</div></div>
    <div class="box"><div class="k">Lucro desejado</div><div class="v" id="profitTarget">R$ 25,00</div></div>
    <div class="box"><div class="k">Saldo alvo</div><div class="v" id="targetBalance">R$ 125,00</div></div>
    </div>

    <div class="box warn">
    <div class="k">Regra geral da sessão</div>
    <div class="note" id="generalRule">O cancelamento específico será exibido junto do sinal gerado.</div>
    </div>

    <button type="submit">Iniciar sessão simulada</button>
    </form>

    <div class="note">
    Contrato: mobile-first, observador visual, motor lógico programado, saldo simulado e segurança travada.
    </div>
    </div>
    </div>

    <script>
    const catalog = {
      support_resistance: {label:"Suporte e resistência", scalper5:1, scalper1h:8, day5:0, day1h:3, risk:"médio"},
      candle_reversal: {label:"Reversão de vela", scalper5:1, scalper1h:10, day5:0, day1h:4, risk:"médio/alto"},
      breakout: {label:"Rompimento", scalper5:1, scalper1h:7, day5:0, day1h:3, risk:"alto"},
      moving_average_trend: {label:"Tendência por médias", scalper5:0, scalper1h:6, day5:0, day1h:2, risk:"médio"},
      pullback: {label:"Pullback", scalper5:1, scalper1h:6, day5:0, day1h:2, risk:"médio"},
      simple_confluence: {label:"Confluência simples", scalper5:1, scalper1h:5, day5:0, day1h:2, risk:"baixo/médio"}
    };
    function brl(v) { return "R$ " + Number(v || 0).toFixed(2).replace(".", ","); }
    function updatePreview() {
      const mode = document.getElementById("operational_mode").value;
      const strategy = document.getElementById("strategy_key").value;
      const bankroll = Number(document.getElementById("initial_bankroll").value || 0);
      const entry = Number(document.getElementById("current_entry").value || 0);
      const desiredProfit = Number(document.getElementById("desired_profit").value || 0);
      const meta = catalog[strategy];
      const s5 = mode === "scalper" ? meta.scalper5 : meta.day5;
      const s1h = mode === "scalper" ? meta.scalper1h : meta.day1h;
      document.getElementById("signals5").innerText = s5 + (s5 === 1 ? " sinal" : " sinais");
      document.getElementById("signals1h").innerText = s1h + (s1h === 1 ? " sinal" : " sinais");
      document.getElementById("riskBox").innerText = meta.risk;
      document.getElementById("consumption").innerText = brl(Math.min(s1h * entry, bankroll));
      document.getElementById("profitTarget").innerText = brl(desiredProfit);
      document.getElementById("targetBalance").innerText = brl(bankroll + desiredProfit);
    }
    updatePreview();
    </script>
    </body>
    </html>"""
        return Response(html, mimetype="text/html; charset=utf-8")

    def _ptp113b31a41_signal_contract_override():
        from flask import jsonify, request
        contract = app.config.get("PTP113B31A_SESSION_CONTRACT") or _ptp113b31a41_build_contract(request.args)
        return jsonify({
            "version": "PTP-113B.3.1A.4.1",
            "status": "COMPLETE_SIMULATED_CONTRACT_WITH_PROFIT_TARGET",
            "contract": contract,
            "available_strategies": _ptp113b31a_strategy_catalog(),
            "available_operational_modes": {
                "scalper": "Scalper — sinais rápidos",
                "day_trade": "Day Trade — sinais mais seletivos",
            },
            "required_visual_fields": contract["required_visual_fields"],
            "example": {
                "ativo": "LATAM Index",
                "direcao": "COMPRA / VENDA / AGUARDAR",
                "horario_entrada": "HH:MM:SS",
                "preco_referencia": "preço ou zona de entrada",
                "tempo_expiracao": contract["expiration"]["label"],
                "explicacao": "Motivo técnico conforme modo operacional e estratégia geradora.",
                "confianca": "0-100%",
                "status": "AGUARDANDO HORÁRIO DE ENTRADA",
                "modo_operacional": contract["operational_mode"]["label"],
                "estrategia_geradora": contract["strategy"]["label"],
                "banca_simulada": contract["bankroll"]["initial_bankroll"],
                "saldo_atual": contract["bankroll"]["current_bankroll"],
                "entrada_simulada": contract["bankroll"]["current_entry"],
                "lucro_desejado_sessao": contract["profit_target"]["desired_profit"],
                "saldo_alvo_sessao": contract["profit_target"]["target_bankroll"],
                "risco": contract["risk"],
                "cancelamento_especifico": "Será definido no sinal conforme ativo, preço, horário de entrada e estratégia.",
                "estimativa_sinais_5m": contract["preview"]["estimated_signals_5m"],
                "estimativa_sinais_1h": contract["preview"]["estimated_signals_1h"],
            },
        })

    @app.after_request
    def _ptp113b31a41_enrich_mobile_state(response):
        try:
            from flask import request
            import json as _json

            if request.path != "/api/mobile/state":
                return response

            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                return response

            contract = app.config.get("PTP113B31A_SESSION_CONTRACT") or _ptp113b31a41_build_contract({})
            mobile_session = data.get("mobile_session")
            if not isinstance(mobile_session, dict):
                mobile_session = {}

            mobile_session["contract"] = contract
            mobile_session["profit_target"] = contract["profit_target"]
            mobile_session["simulated_bankroll"] = contract["bankroll"]
            mobile_session["operational_mode"] = contract["operational_mode"]
            mobile_session["strategy"] = contract["strategy"]
            mobile_session["preview"] = contract["preview"]

            data["mobile_session"] = mobile_session
            data["profit_target"] = contract["profit_target"]
            data["simulation_only"] = True
            data["orders_enabled"] = False
            data["real_money_enabled"] = False
            data["auto_click_enabled"] = False
            data["ptp113b31a41_profit_target_ready"] = True

            response.set_data(_json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        except Exception as exc:
            response.headers["X-PTP113B31A41-State-Enrich-Error"] = str(exc)[:180]
        return response

    _ptp113b31a41_has_post = False
    for _rule in list(app.url_map.iter_rules()):
        if _rule.rule == "/session/setup":
            app.view_functions[_rule.endpoint] = _ptp113b31a41_session_setup_override
            if "POST" in _rule.methods:
                _ptp113b31a41_has_post = True

        if _rule.rule == "/api/mobile/signal/contract":
            app.view_functions[_rule.endpoint] = _ptp113b31a41_signal_contract_override

    if not _ptp113b31a41_has_post:
        app.add_url_rule(
            "/session/setup",
            "ptp113b31a41_session_setup_post",
            _ptp113b31a41_session_setup_override,
            methods=["POST"],
        )
    # END PTP-113B.3.1A.4.1 PROFIT TARGET OVERRIDE

    # END PTP-113B.3.1A COMPLETE SESSION CONTRACT

    return app


def _run_audit_logic_smoke_test() -> bool:
    def insert_signal(
        *,
        created_at: datetime,
        direction: str = "ALTA",
        entry_price: float = 4182.00,
        expiration_seconds: int = DEFAULT_EXPIRATION_SECONDS,
        status: str = WAITING_RESULT_STATUS,
    ) -> int:
        _ensure_signal_db()
        with sqlite3.connect(SIGNALS_DB_PATH) as conn:
            cursor = conn.execute(
                """
                INSERT INTO signals (
                    created_at, asset, price, signal, direction, confidence,
                    expiration_seconds, reason, source, status, result,
                    metadata_json, entry_price
                )
                VALUES (?, 'Cafeina Index', ?, ?, ?, 55, ?, 'smoke', 'smoke',
                        ?, ?, '{}', ?)
                """,
                (
                    created_at.isoformat(),
                    entry_price,
                    "OBSERVAR ALTA" if direction == "ALTA" else "OBSERVAR BAIXA",
                    direction,
                    expiration_seconds,
                    status,
                    status,
                    entry_price,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_signal(signal_id: int) -> dict[str, Any]:
        with sqlite3.connect(SIGNALS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM signals WHERE id = ?",
                (signal_id,),
            ).fetchone()
        return dict(row) if row is not None else {}

    def clear_audit_tables() -> None:
        _ensure_signal_db()
        with sqlite3.connect(SIGNALS_DB_PATH) as conn:
            conn.execute("DELETE FROM signals")
            conn.execute("DELETE FROM price_ticks")
            conn.commit()

    cases = [
        ("BAIXA", 4182.00, 4181.90, "WIN"),
        ("BAIXA", 4182.00, 4182.10, "LOSS"),
        ("ALTA", 4182.00, 4182.10, "WIN"),
        ("ALTA", 4182.00, 4181.90, "LOSS"),
        ("ALTA", 4182.00, 4182.00, "DRAW"),
    ]
    for direction, entry_price, result_price, expected in cases:
        result, _ = _evaluate_signal_result(direction, entry_price, result_price)
        if result != expected:
            raise AssertionError(
                f"Audit logic failed: {direction} {entry_price} -> {result_price} expected {expected}, got {result}"
            )

    if DEFAULT_READER_INTERVAL_SECONDS != 3:
        raise AssertionError("Reader interval must default to 3s")
    if SIGNAL_ANALYSIS_INTERVAL_SECONDS != 3 or SIGNAL_COOLDOWN_SECONDS != 3:
        raise AssertionError("Signal analysis/cooldown must be 3s")

    now = _now()
    clear_audit_tables()
    _insert_price_tick(
        created_at=now.isoformat(),
        asset="Cafeina Index",
        price=4182.10,
        source="smoke",
        metadata={"reader_interval_seconds": DEFAULT_READER_INTERVAL_SECONDS},
    )
    if _price_ticks_count() < 1:
        raise AssertionError("price_ticks insert/count failed")

    state = {
        "signal": "OBSERVAR ALTA",
        "asset": "Cafeina Index",
        "price": 4182.10,
        "confidence": 55,
        "valid_readings": 10,
    }
    _register_signal_if_needed(state, DEFAULT_EXPIRATION_SECONDS)
    state["signal"] = "OBSERVAR BAIXA"
    _register_signal_if_needed(state, DEFAULT_EXPIRATION_SECONDS)
    with sqlite3.connect(SIGNALS_DB_PATH) as conn:
        signal_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    if signal_count != 1:
        raise AssertionError("Signal cooldown 3s failed")

    clear_audit_tables()

    emitted_at = now - timedelta(seconds=41)
    target_dt = emitted_at + timedelta(seconds=DEFAULT_EXPIRATION_SECONDS)
    exact_history = [
        {
            "timestamp": target_dt.isoformat(),
            "asset": "Cafeina Index",
            "price_value": 4182.10,
            "source": "smoke",
        }
    ]
    exact_price, exact_metadata = _history_price_near_target(
        exact_history,
        target_dt,
        expected_asset="Cafeina Index",
    )
    result, _ = _evaluate_signal_result("ALTA", 4182.00, exact_price)
    if result != "WIN":
        raise AssertionError("Audit history target_time test failed")
    if exact_metadata.get("result_price_source") != "json":
        raise AssertionError("Audit history source metadata failed")

    late_history = [
        {
            "timestamp": (target_dt + timedelta(seconds=10)).isoformat(),
            "asset": "Cafeina Index",
            "price_value": 4181.90,
            "source": "smoke",
        }
    ]
    late_price, _ = _history_price_near_target(late_history, target_dt, expected_asset="Cafeina Index")
    result, _ = _evaluate_signal_result("BAIXA", 4182.00, late_price)
    if result != "WIN":
        raise AssertionError("Audit history +10s WIN test failed")
    result, _ = _evaluate_signal_result("ALTA", 4182.00, late_price)
    if result != "LOSS":
        raise AssertionError("Audit history +10s LOSS test failed")

    before_history = [
        {
            "timestamp": (target_dt - timedelta(seconds=1)).isoformat(),
            "asset": "Cafeina Index",
            "price_value": 4182.10,
            "source": "smoke",
        }
    ]
    before_price, before_metadata = _history_price_near_target(
        before_history,
        target_dt,
        expected_asset="Cafeina Index",
    )
    if before_price != 4182.10 or before_metadata.get("result_price_match") != "nearest_within_tolerance":
        raise AssertionError("Audit nearest pre-expiration tolerance test failed")

    stale_history = [
        {
            "timestamp": (target_dt + timedelta(seconds=11)).isoformat(),
            "asset": "Cafeina Index",
            "price_value": 4182.10,
            "source": "smoke",
        }
    ]
    stale_price, stale_metadata = _history_price_near_target(stale_history, target_dt, expected_asset="Cafeina Index")
    result, _ = _evaluate_signal_result("ALTA", 4182.00, stale_price)
    if result != "UNKNOWN" or stale_metadata.get("result_reason") != UNKNOWN_NO_HISTORY_REASON:
        raise AssertionError("Audit history post-margin UNKNOWN test failed")

    clear_audit_tables()

    waiting_id = insert_signal(created_at=now - timedelta(seconds=31))
    _check_pending_signals([])
    waiting_row = get_signal(waiting_id)
    if waiting_row.get("status") != WAITING_RESULT_STATUS:
        raise AssertionError("WAITING_RESULT before UNKNOWN failed")

    unknown_id = insert_signal(created_at=now - timedelta(seconds=76))
    _check_pending_signals([])
    unknown_row = get_signal(unknown_id)
    if unknown_row.get("status") != "UNKNOWN" or unknown_row.get("result") != "UNKNOWN":
        raise AssertionError("UNKNOWN after final margin failed")

    clear_audit_tables()

    win_created = now - timedelta(seconds=36)
    win_target = win_created + timedelta(seconds=DEFAULT_EXPIRATION_SECONDS)
    win_id = insert_signal(created_at=win_created, direction="BAIXA", entry_price=4182.00)
    _check_pending_signals(
        [
            {
                "timestamp": (win_target + timedelta(seconds=5)).isoformat(),
                "asset": "Cafeina Index",
                "price_value": 4181.90,
                "source": "smoke",
            }
        ]
    )
    win_row = get_signal(win_id)
    if win_row.get("result") != "WIN":
        raise AssertionError("JSON result price between 30s and 40s failed")

    clear_audit_tables()

    sqlite_win_created = now - timedelta(seconds=36)
    sqlite_win_target = sqlite_win_created + timedelta(seconds=DEFAULT_EXPIRATION_SECONDS)
    sqlite_baixa_id = insert_signal(
        created_at=sqlite_win_created,
        direction="BAIXA",
        entry_price=4182.00,
    )
    _insert_price_tick(
        created_at=(sqlite_win_target + timedelta(seconds=5)).isoformat(),
        asset="Cafeina Index",
        price=4181.90,
        source="smoke",
        metadata={"window_title": "4181.90 Cafeina Index - OlympTrade"},
    )
    _check_pending_signals([])
    sqlite_baixa_row = get_signal(sqlite_baixa_id)
    if sqlite_baixa_row.get("result") != "WIN":
        raise AssertionError("SQLite fallback BAIXA WIN test failed")
    sqlite_baixa_metadata = _metadata_from_json(sqlite_baixa_row.get("metadata_json"))
    if sqlite_baixa_metadata.get("result_price_source") != "sqlite_price_ticks":
        raise AssertionError("SQLite fallback source metadata failed")

    clear_audit_tables()

    sqlite_alta_created = now - timedelta(seconds=36)
    sqlite_alta_target = sqlite_alta_created + timedelta(seconds=DEFAULT_EXPIRATION_SECONDS)
    sqlite_alta_id = insert_signal(
        created_at=sqlite_alta_created,
        direction="ALTA",
        entry_price=4182.00,
    )
    _insert_price_tick(
        created_at=(sqlite_alta_target + timedelta(seconds=5)).isoformat(),
        asset="Cafeina Index",
        price=4182.20,
        source="smoke",
        metadata={"window_title": "4182.20 Cafeina Index - OlympTrade"},
    )
    _check_pending_signals([])
    sqlite_alta_row = get_signal(sqlite_alta_id)
    if sqlite_alta_row.get("result") != "WIN":
        raise AssertionError("SQLite fallback ALTA WIN test failed")

    clear_audit_tables()

    missing_id = insert_signal(created_at=now - timedelta(seconds=76), direction="ALTA", entry_price=4182.00)
    _check_pending_signals([])
    missing_row = get_signal(missing_id)
    if missing_row.get("result") != "UNKNOWN" or missing_row.get("result_price") is not None:
        raise AssertionError("Missing JSON and SQLite UNKNOWN test failed")

    if _hit_rate_percent(win=1, loss=1, draw=1) != 33.3:
        raise AssertionError("Audit hit-rate UNKNOWN/PENDING ignore test failed")
    if _hit_rate_percent(win=0, loss=0, draw=0) != 0.0:
        raise AssertionError("UNKNOWN-only hit-rate test failed")

    clear_audit_tables()

    old_created = now - timedelta(seconds=110)
    old_target = old_created + timedelta(seconds=60)
    old_id = insert_signal(
        created_at=old_created,
        direction="BAIXA",
        entry_price=4182.00,
        expiration_seconds=60,
        status="UNKNOWN",
    )
    _insert_price_tick(
        created_at=(old_target + timedelta(seconds=5)).isoformat(),
        asset="Cafeina Index",
        price=4181.80,
        source="smoke",
        metadata={"window_title": "4181.80 Cafeina Index - OlympTrade"},
    )
    _backfill_unknown_signals([])
    old_row = get_signal(old_id)
    old_metadata = _metadata_from_json(old_row.get("metadata_json"))
    if old_row.get("result") != "WIN" or int(old_row.get("expiration_seconds")) != 60:
        raise AssertionError("60s legacy signal backfill failed")
    if old_metadata.get("target_time") != old_target.isoformat():
        raise AssertionError("60s legacy signal target_time was not preserved")
    return True


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    _ensure_signal_db()
    local_ip = _local_ip()
    print("PredixAI Trader Mobile Server")
    print(OBSERVATION_NOTICE)
    print(SIMULATION_NOTICE)
    print(f"Local PC: http://127.0.0.1:{port}/mobile")
    print(f"Celular na mesma Wi-Fi: http://{local_ip}:{port}/mobile")
    print("Endpoints simulados: POST /mobile/session/start | POST /api/mobile/simulated-session/start | POST /api/mobile/start")
    print("Endpoint observador legado: POST /api/mobile/stop")
    reader_warning = _reader_warning(_active_reader_processes())
    if reader_warning:
        print(reader_warning)
    if HAS_FLASK:
        create_mobile_app().run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
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
    global RUNTIME_DIR, LAST_READING_PATH, PRICE_HISTORY_PATH
    global REJECTED_READINGS_PATH, SIGNALS_DB_PATH, MOBILE_SESSION_PATH

    original_paths = (
        RUNTIME_DIR,
        LAST_READING_PATH,
        PRICE_HISTORY_PATH,
        REJECTED_READINGS_PATH,
        SIGNALS_DB_PATH,
        MOBILE_SESSION_PATH,
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        RUNTIME_DIR = Path(tmp_dir)
        LAST_READING_PATH = RUNTIME_DIR / "last_live_reading.json"
        PRICE_HISTORY_PATH = RUNTIME_DIR / "live_price_history.json"
        REJECTED_READINGS_PATH = RUNTIME_DIR / "rejected_live_readings.json"
        SIGNALS_DB_PATH = RUNTIME_DIR / "predixai_trader_signals.db"
        MOBILE_SESSION_PATH = RUNTIME_DIR / "mobile_current_session.json"

        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        now = _now()
        sample_tick = {
            "status": "READY",
            "source": "smoke",
            "timestamp": now.isoformat(),
            "asset": "Cafeina Index",
            "price": "4182.10",
            "price_value": 4182.10,
            "confidence": 100.0,
        }
        LAST_READING_PATH.write_text(
            json.dumps(sample_tick, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        PRICE_HISTORY_PATH.write_text(
            json.dumps([sample_tick], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        REJECTED_READINGS_PATH.write_text("[]", encoding="utf-8")

        try:
            _ensure_signal_db()
            audit_logic_ok = _run_audit_logic_smoke_test()
            _insert_price_tick(
                created_at=now.isoformat(),
                asset="Cafeina Index",
                price=4182.10,
                source="smoke",
                metadata={
                    "reader_interval_seconds": DEFAULT_READER_INTERVAL_SECONDS,
                    "simulation_only": True,
                },
            )
            if HAS_FLASK:
                app = create_mobile_app()
                with app.test_client() as client:
                    mobile_response = client.get("/mobile")
                    state_response = client.get("/api/mobile/state")
                    payload = state_response.get_json(silent=True) or {}
                    mobile_status = mobile_response.status_code
                    state_status = state_response.status_code
            else:
                mobile_status, _, _ = _handle_get("/mobile")
                state_status, _, state_body = _handle_get(
                    "/api/mobile/state",
                    host_header=f"127.0.0.1:{port}",
                )
                payload = json.loads(state_body.decode("utf-8"))

            diagnostics = payload.get("price_diagnostics", {})
            smoke_ok = (
                mobile_status == 200
                and state_status == 200
                and "state" in payload
                and audit_logic_ok
                and diagnostics.get("price_ticks_count", 0) >= 1
            )
            print(f"SMOKE_MOBILE_STATUS={mobile_status}")
            print(f"SMOKE_STATE_STATUS={state_status}")
            print(f"SMOKE_HAS_STATE={'state' in payload}")
            print(f"SMOKE_PRICE_READER_3S={DEFAULT_READER_INTERVAL_SECONDS == 3 and diagnostics.get('price_ticks_count', 0) >= 1}")
            print(f"SMOKE_SIGNAL_INTERVAL_3S={SIGNAL_ANALYSIS_INTERVAL_SECONDS == 3 and SIGNAL_COOLDOWN_SECONDS == 3}")
            print(f"SMOKE_RESULT_WINDOW_30_40={audit_logic_ok}")
            print(f"SMOKE_WAITING_BEFORE_UNKNOWN={audit_logic_ok}")
            print(f"SMOKE_UNKNOWN_AFTER_FINAL_MARGIN={audit_logic_ok}")
            print(f"SMOKE_AUDIT_LOGIC={audit_logic_ok}")
            print(f"SMOKE_MOBILE_URL=http://{_local_ip()}:{port}/mobile")
            return 0 if smoke_ok else 1
        finally:
            (
                RUNTIME_DIR,
                LAST_READING_PATH,
                PRICE_HISTORY_PATH,
                REJECTED_READINGS_PATH,
                SIGNALS_DB_PATH,
                MOBILE_SESSION_PATH,
            ) = original_paths


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



# PTP-113B.3.1A.5.1_SERVER_RECOVERY_RISK_HOOK_V2
import json as _ptp113b3151_json_v2
import re as _ptp113b3151_re_v2


def _ptp113b3151_num_v2(value, default=0.0):
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ptp113b3151_bool_v2(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "sim", "yes", "on"}


def _ptp113b3151_mode_v2(mode, enabled=True):
    raw = str(mode or "NONE").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SEM_RECUPERACAO": "NONE",
        "SEM_RECUPERAÇÃO": "NONE",
        "FIXED": "MAO_FIXA",
        "MAO_FIXA": "MAO_FIXA",
        "MÃO_FIXA": "MAO_FIXA",
        "SOROS": "SOROS",
        "SOFT_MARTINGALE": "MARTINGALE_1",
        "MARTINGALE": "MARTINGALE_1",
        "MARTINGALE_1": "MARTINGALE_1",
        "MARTINGALE_2": "MARTINGALE_2",
        "CUSTOM": "SMARTGALE",
        "SMARTGALE": "SMARTGALE",
        "NONE": "NONE",
    }
    normalized = aliases.get(raw, raw)
    return normalized if enabled else "NONE"


def _ptp113b3151_plan_v2(bankroll, entry, stop_loss, max_entry_limit, payout, mode, enabled, max_steps, strategy_risk="médio"):
    bankroll = max(0.01, _ptp113b3151_num_v2(bankroll, 100.0))
    entry = max(0.01, _ptp113b3151_num_v2(entry, 5.0))
    stop_loss = max(0.0, _ptp113b3151_num_v2(stop_loss, 20.0))
    max_entry_limit = max(0.01, _ptp113b3151_num_v2(max_entry_limit, min(bankroll, stop_loss or bankroll)))
    payout = max(0.0, _ptp113b3151_num_v2(payout, 80.0))
    mode = _ptp113b3151_mode_v2(mode, enabled)
    max_steps = max(0, int(_ptp113b3151_num_v2(max_steps, 0)))
    cap = min(bankroll, stop_loss if stop_loss else bankroll, max_entry_limit)

    if mode == "NONE":
        sequence = [entry]
        max_steps = 0
        reason = "Sem recuperação."
    elif mode == "MAO_FIXA":
        max_steps = max(1, min(max_steps or 2, 5))
        sequence = [entry for _ in range(max_steps + 1)]
        reason = "Mão fixa: entrada fixa após perda."
    elif mode == "SOROS":
        max_steps = max(1, min(max_steps or 2, 3))
        sequence = [entry]
        for _ in range(max_steps):
            sequence.append(sequence[-1] * 1.5)
        reason = "Soros/anti-martingale simulado."
    elif mode == "MARTINGALE_1":
        max_steps = 1
        sequence = [entry, entry * 2]
        reason = "1 Martingale simulado."
    elif mode == "MARTINGALE_2":
        max_steps = 2
        sequence = [entry, entry * 2, entry * 4]
        reason = "2 Martingales simulados."
    elif mode == "SMARTGALE":
        max_steps = 2
        sequence = [entry, entry * 1.6, entry * 2.2]
        reason = "SmartGale simulado com progressão limitada."
    else:
        sequence = [entry]
        reason = "Modo não reconhecido tratado como entrada base."

    sequence = [round(min(max(0.01, x), cap), 2) for x in sequence]
    exposure = round(sum(sequence), 2)
    max_entry = round(max(sequence), 2)
    next_entry = round(sequence[1] if len(sequence) > 1 else sequence[0], 2)
    exposure_percent = round((exposure / bankroll) * 100, 2) if bankroll else 0.0

    risk_score = 0
    if exposure_percent > 10:
        risk_score += 1
    if exposure_percent > 25:
        risk_score += 1
    if exposure_percent > 50:
        risk_score += 2
    if mode.startswith("MARTINGALE"):
        risk_score += 1
    if mode == "MARTINGALE_2":
        risk_score += 1
    if payout < 70:
        risk_score += 1
    if "alto" in str(strategy_risk).lower():
        risk_score += 1
    if exposure > stop_loss > 0:
        risk_score += 2

    if risk_score <= 1:
        combined = "BAIXO"
        alert = "Risco simulado baixo."
    elif risk_score <= 3:
        combined = "MODERADO"
        alert = "Risco simulado moderado. Monitorar sequência de perdas."
    else:
        combined = "ALTO"
        alert = "Risco simulado alto. Reduzir entrada, recuperação ou stop."

    return {
        "mode": mode,
        "enabled": mode != "NONE",
        "max_recovery_steps": max_steps,
        "entry_sequence": sequence,
        "next_entry": next_entry,
        "max_entry": max_entry,
        "exposure_max": exposure,
        "exposure_percent": exposure_percent,
        "combined_risk": combined,
        "risk_alert": alert,
        "reason": reason,
        "payout_reference": payout,
    }


def _ptp113b3151_enrich_dict_v2(data):
    if not isinstance(data, dict):
        return data

    contract = data.get("contract") if isinstance(data.get("contract"), dict) else data
    mobile_session = data.get("mobile_session") if isinstance(data.get("mobile_session"), dict) else None
    if mobile_session:
        contract = mobile_session

    bankroll = contract.setdefault("bankroll", {})
    risk = contract.setdefault("risk", {})
    recovery = contract.setdefault("recovery", {})

    current_bankroll = _ptp113b3151_num_v2(
        bankroll.get("current_bankroll") or data.get("current_bankroll") or data.get("balance"),
        _ptp113b3151_num_v2(bankroll.get("initial_bankroll"), 100.0),
    )
    initial_entry = _ptp113b3151_num_v2(
        bankroll.get("current_entry") or bankroll.get("initial_entry") or data.get("current_entry"),
        5.0,
    )
    stop_loss = _ptp113b3151_num_v2(risk.get("stop_loss") or data.get("stop_loss"), 20.0)
    max_entry_limit = _ptp113b3151_num_v2(risk.get("max_entry_limit") or data.get("max_entry_limit"), min(current_bankroll, stop_loss or current_bankroll))
    payout = _ptp113b3151_num_v2(risk.get("payout_min") or data.get("payout") or data.get("payout_min"), 80.0)
    enabled = _ptp113b3151_bool_v2(recovery.get("recovery_enabled", recovery.get("enabled", False)))
    mode = _ptp113b3151_mode_v2(recovery.get("recovery_mode") or recovery.get("mode"), enabled)
    max_steps = int(_ptp113b3151_num_v2(recovery.get("max_recovery_steps"), 0))

    plan = _ptp113b3151_plan_v2(
        bankroll=current_bankroll,
        entry=initial_entry,
        stop_loss=stop_loss,
        max_entry_limit=max_entry_limit,
        payout=payout,
        mode=mode,
        enabled=enabled,
        max_steps=max_steps,
        strategy_risk=(contract.get("strategy") or {}).get("risk", "médio"),
    )

    risk["max_entry_limit"] = max_entry_limit
    recovery.update({
        "recovery_enabled": plan["enabled"],
        "recovery_mode": plan["mode"],
        "max_recovery_steps": plan["max_recovery_steps"],
        "entry_sequence": plan["entry_sequence"],
        "next_entry": plan["next_entry"],
        "max_entry": plan["max_entry"],
        "exposure_max": plan["exposure_max"],
        "exposure_percent": plan["exposure_percent"],
        "combined_risk": plan["combined_risk"],
        "risk_alert": plan["risk_alert"],
        "recovery_plan": plan,
    })

    risk_management = {
        "payout": payout,
        "stop_loss": stop_loss,
        "max_entry_limit": max_entry_limit,
        "recovery_plan": plan,
        "combined_risk": plan["combined_risk"],
        "risk_alert": plan["risk_alert"],
    }

    contract["risk_management"] = risk_management
    data["risk_management"] = risk_management
    data["recovery_plan"] = plan
    return data


def _ptp113b3151_enhance_session_setup_html_v2(html):
    if not isinstance(html, str) or "recovery_mode" not in html:
        return html

    new_select = "\n".join([
        '<select name="recovery_mode" id="recovery_mode">',
        '  <option value="NONE">Sem recuperação</option>',
        '  <option value="MAO_FIXA">Mão fixa / entrada fixa</option>',
        '  <option value="SOROS">Soros / anti-martingale</option>',
        '  <option value="MARTINGALE_1">1 Martingale</option>',
        '  <option value="MARTINGALE_2">2 Martingales</option>',
        '  <option value="SMARTGALE">SmartGale simulado</option>',
        '</select>',
    ])

    html = _ptp113b3151_re_v2.sub(
        r"<select[^>]+name=[\"']recovery_mode[\"'][^>]*>.*?</select>",
        new_select,
        html,
        flags=_ptp113b3151_re_v2.S,
    )

    if 'name="max_entry_limit"' not in html:
        html = html.replace(
            '<label>Perfil de risco</label>',
            '<label>Limite máximo de entrada simulada</label><input name="max_entry_limit" id="max_entry_limit" type="number" min="1" step="0.01" value="20.00"/><label>Perfil de risco</label>',
            1,
        )

    if "PTP-113B.3.1A.5.1_RECOVERY_PREVIEW_V2" not in html and "</form>" in html:
        preview = '<div class="box" id="recoveryPreview" data-ptp="PTP-113B.3.1A.5.1_RECOVERY_PREVIEW_V2"><div class="k">Gestão simulada de recuperação e risco</div><div class="v">O contrato calcula sequência de entradas, próxima entrada, entrada máxima, exposição máxima, risco combinado e alerta.</div></div>'
        html = html.replace("</form>", preview + "\n</form>", 1)

    return html


try:
    _ptp113b3151_original_create_mobile_app_v2 = create_mobile_app

    def create_mobile_app(*args, **kwargs):  # type: ignore[no-redef]
        app = _ptp113b3151_original_create_mobile_app_v2(*args, **kwargs)

        if not getattr(app, "_ptp113b3151_recovery_risk_hook_v2", False):
            @app.after_request
            def _ptp113b3151_after_request_v2(response):
                try:
                    if request.path == "/session/setup":
                        content_type = str(response.headers.get("Content-Type", ""))
                        if "text/html" in content_type:
                            html = response.get_data(as_text=True)
                            html = _ptp113b3151_enhance_session_setup_html_v2(html)
                            response.set_data(html)
                            response.headers["Content-Length"] = str(len(response.get_data()))
                        return response

                    if request.path in {"/api/mobile/state", "/api/mobile/signal/contract"}:
                        data = response.get_json(silent=True)
                        if isinstance(data, dict):
                            data = _ptp113b3151_enrich_dict_v2(data)
                            response.set_data(_ptp113b3151_json_v2.dumps(data, ensure_ascii=False, default=str))
                            response.mimetype = "application/json"
                    return response
                except Exception as exc:
                    response.headers["X-PTP113B3151-Warning"] = str(exc)[:120]
                    return response

            app._ptp113b3151_recovery_risk_hook_v2 = True

        return app
except NameError:
    pass



# PTP-113B.3.1A.5.1_SETUP_UI_FORCE_HOOK_V3
import re as _ptp113b3151_setup_re_v3


def _ptp113b3151_setup_ui_block_v3():
    return "\n".join([
        '<section class="box" data-ptp="PTP-113B.3.1A.5.1_SETUP_UI_FORCE_HOOK_V3">',
        '  <h2>Recuperação e risco simulados</h2>',
        '  <label>Recuperação simulada</label>',
        '  <select name="recovery_mode" id="recovery_mode">',
        '    <option value="NONE">Sem recuperação</option>',
        '    <option value="MAO_FIXA">Mão fixa / entrada fixa</option>',
        '    <option value="SOROS">Soros / anti-martingale</option>',
        '    <option value="MARTINGALE_1">1 Martingale</option>',
        '    <option value="MARTINGALE_2">2 Martingales</option>',
        '    <option value="SMARTGALE">SmartGale simulado</option>',
        '  </select>',
        '  <label>Limite máximo de entrada simulada</label>',
        '  <input name="max_entry_limit" id="max_entry_limit" type="number" min="1" step="0.01" value="20.00"/>',
        '  <div class="box">',
        '    <div class="k">Prévia de risco</div>',
        '    <div class="v">O contrato calcula sequência de entradas, próxima entrada, entrada máxima, exposição máxima, percentual da banca exposto, risco combinado e alerta.</div>',
        '  </div>',
        '</section>',
    ])


def _ptp113b3151_force_setup_ui_v3(html):
    if not isinstance(html, str):
        return html

    if "PTP-113B.3.1A.5.1_SETUP_UI_FORCE_HOOK_V3" in html:
        return html

    block = _ptp113b3151_setup_ui_block_v3()

    # Se já houver select recovery antigo, substitui por versão completa.
    if 'name="recovery_mode"' in html or "name='recovery_mode'" in html:
        full_select = "\n".join([
            '<select name="recovery_mode" id="recovery_mode">',
            '  <option value="NONE">Sem recuperação</option>',
            '  <option value="MAO_FIXA">Mão fixa / entrada fixa</option>',
            '  <option value="SOROS">Soros / anti-martingale</option>',
            '  <option value="MARTINGALE_1">1 Martingale</option>',
            '  <option value="MARTINGALE_2">2 Martingales</option>',
            '  <option value="SMARTGALE">SmartGale simulado</option>',
            '</select>',
        ])
        html = _ptp113b3151_setup_re_v3.sub(
            r"<select[^>]+name=[\"']recovery_mode[\"'][^>]*>.*?</select>",
            full_select,
            html,
            flags=_ptp113b3151_setup_re_v3.S,
        )

    # Injeta bloco completo antes do fechamento do formulário.
    if "</form>" in html:
        html = html.replace("</form>", block + "\n</form>", 1)
    else:
        html += "\n" + block

    return html


try:
    _ptp113b3151_original_create_mobile_app_v3 = create_mobile_app

    def create_mobile_app(*args, **kwargs):  # type: ignore[no-redef]
        app = _ptp113b3151_original_create_mobile_app_v3(*args, **kwargs)

        if not getattr(app, "_ptp113b3151_setup_ui_force_hook_v3", False):
            @app.after_request
            def _ptp113b3151_setup_ui_after_request_v3(response):
                try:
                    if request.path == "/session/setup":
                        content_type = str(response.headers.get("Content-Type", ""))
                        if "text/html" in content_type:
                            html = response.get_data(as_text=True)
                            html = _ptp113b3151_force_setup_ui_v3(html)
                            response.set_data(html)
                            response.headers["Content-Length"] = str(len(response.get_data()))
                    return response
                except Exception as exc:
                    response.headers["X-PTP113B3151-SetupUI-Warning"] = str(exc)[:120]
                    return response

            app._ptp113b3151_setup_ui_force_hook_v3 = True

        return app
except NameError:
    pass



# PTP-113B.3.1A.5.1A_CURRENCY_CONTROLS_BRL_V1
def _ptp113b3151a_currency_controls_v1_assets():
    css = """
<style id="ptp113b3151a-currency-style">
  input[type=number]::-webkit-outer-spin-button,
  input[type=number]::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  input[type=number] {
    -moz-appearance: textfield;
  }

  .money-stepper {
    display: grid;
    grid-template-columns: 52px 1fr 52px;
    gap: 8px;
    align-items: center;
    margin: 6px 0 14px 0;
  }

  .money-stepper button {
    min-height: 44px;
    border-radius: 12px;
    border: 1px solid #31516f;
    background: #102239;
    color: #f5c542;
    font-size: 24px;
    font-weight: 800;
    cursor: pointer;
  }

  .money-stepper button:active {
    transform: scale(0.98);
  }

  .money-stepper input {
    width: 100%;
    min-height: 44px;
    border-radius: 12px;
    border: 1px solid #31516f;
    background: #061423;
    color: #ffffff;
    padding: 0 14px;
    font-size: 16px;
    font-weight: 700;
  }

  .money-hidden-source {
    display: none !important;
  }

  .money-help {
    color: #8ea4b9;
    font-size: 12px;
    margin-top: -8px;
    margin-bottom: 10px;
  }
</style>
"""

    js = """
<script id="ptp113b3151a-currency-script">
(function () {
  const MONEY_FIELDS = [
    "initial_bankroll",
    "simulated_bankroll",
    "initial_entry",
    "entry_value",
    "profit_target",
    "take_profit",
    "max_entry_limit",
    "stop_loss"
  ];

  function parseMoney(value) {
    // PTP-113B.3.1A.5.1A.8_NORMALIZE_PARSE_BRL
    if (value === null || value === undefined) return 0;

    let text = String(value).trim();
    if (!text) return 0;

    text = text
      .replace(/\u00A0/g, " ")
      .replace(/[^\d,.\-]/g, "")
      .trim();

    if (!text) return 0;

    const negative = text.indexOf("-") !== -1;
    text = text.replace(/-/g, "");

    const hasComma = text.indexOf(",") !== -1;
    const hasDot = text.indexOf(".") !== -1;
    let normalized = text;

    if (hasComma && hasDot) {
      const lastComma = text.lastIndexOf(",");
      const lastDot = text.lastIndexOf(".");

      if (lastComma > lastDot) {
        // Padrão BR: 1.234,56
        normalized = text.replace(/\./g, "").replace(",", ".");
      } else {
        // Padrão internacional: 1,234.56
        normalized = text.replace(/,/g, "");
      }
    } else if (hasComma) {
      const parts = text.split(",");

      if (parts.length > 2) {
        const cents = parts.pop();
        normalized = parts.join("") + "." + cents;
      } else {
        const whole = parts[0] || "0";
        const cents = parts[1] || "";

        if (cents.length === 0) {
          normalized = whole;
        } else if (cents.length <= 2) {
          normalized = whole + "." + cents;
        } else {
          // Caso raro: 1,000 tratado como milhar.
          normalized = whole + cents;
        }
      }
    } else if (hasDot) {
      const parts = text.split(".");

      if (parts.length > 2) {
        const last = parts[parts.length - 1] || "";

        if (last.length <= 2) {
          normalized = parts.slice(0, -1).join("") + "." + last;
        } else {
          normalized = parts.join("");
        }
      } else {
        const whole = parts[0] || "0";
        const tail = parts[1] || "";

        if (tail.length === 0) {
          normalized = whole;
        } else if (tail.length <= 2) {
          normalized = whole + "." + tail;
        } else {
          // Caso BR com ponto de milhar: 1.000
          normalized = whole + tail;
        }
      }
    }

    let number = Number.parseFloat(normalized);
    if (!Number.isFinite(number)) return 0;

    if (negative) number = -number;

    return Math.round(number * 100) / 100;
  }

  function toDecimal(value) {
    return Number(value || 0).toFixed(2);
  }

  function formatBRL(value) {
    const number = Number(value || 0);
    return number.toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function createMoneyControl(source) {
    if (!source || source.dataset.moneyField === "1") return;

    const current = parseMoney(source.value || source.getAttribute("value") || "0");
    source.value = toDecimal(current);
    source.dataset.moneyField = "1";
    source.classList.add("money-hidden-source");
    source.setAttribute("step", "1.00");

    const wrapper = document.createElement("div");
    wrapper.className = "money-stepper";
    wrapper.dataset.moneyStepperFor = source.name || source.id || "money";

    const minus = document.createElement("button");
    minus.type = "button";
    minus.textContent = "−";
    minus.setAttribute("aria-label", "Diminuir R$ 1,00");

    const visible = document.createElement("input");
    visible.type = "text";
    visible.inputMode = "decimal";
    visible.autocomplete = "off";
    visible.value = formatBRL(current);
    visible.setAttribute("aria-label", "Valor em reais");

    const plus = document.createElement("button");
    plus.type = "button";
    plus.textContent = "+";
    plus.setAttribute("aria-label", "Aumentar R$ 1,00");

    function sync(value) {
      const min = parseMoney(source.getAttribute("min") || "0");
      let next = Number(value || 0);
      if (!Number.isFinite(next)) next = 0;
      if (next < min) next = min;
      source.value = toDecimal(next);
      visible.value = formatBRL(next);

      source.dispatchEvent(new Event("input", { bubbles: true }));
      source.dispatchEvent(new Event("change", { bubbles: true }));
    }

    minus.addEventListener("click", function () {
      sync(parseMoney(source.value) - 1);
    });

    plus.addEventListener("click", function () {
      sync(parseMoney(source.value) + 1);
    });

    visible.addEventListener("focus", function () {
      visible.value = toDecimal(parseMoney(source.value)).replace(".", ",");
      visible.select();
    });

    visible.addEventListener("blur", function () {
      sync(parseMoney(visible.value));
    });

    visible.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        sync(parseMoney(visible.value));
        visible.blur();
      }
    });

    wrapper.appendChild(minus);
    wrapper.appendChild(visible);
    wrapper.appendChild(plus);

    source.parentNode.insertBefore(wrapper, source.nextSibling);

    const help = document.createElement("div");
    help.className = "money-help";
    help.textContent = "Ajuste em R$ 1,00 por clique. Valor enviado ao contrato como decimal monetário.";
    wrapper.parentNode.insertBefore(help, wrapper.nextSibling);
  }

  function applyMoneyControls() {
    MONEY_FIELDS.forEach(function (name) {
      document.querySelectorAll('[name="' + name + '"]').forEach(createMoneyControl);
    });
  }

  document.addEventListener("DOMContentLoaded", applyMoneyControls);
  setTimeout(applyMoneyControls, 250);

  document.addEventListener("submit", function () {
    document.querySelectorAll("[data-money-field='1']").forEach(function (source) {
      source.value = toDecimal(parseMoney(source.value));
    });
  }, true);

  window.PTP113B3151A_CURRENCY_CONTROLS_BRL = true;
})();
</script>
"""
    return css + "\n" + js


def _ptp113b3151a_inject_currency_controls_v1(html):
    if not isinstance(html, str):
        return html

    if "PTP113B3151A_CURRENCY_CONTROLS_BRL" in html:
        return html

    assets = _ptp113b3151a_currency_controls_v1_assets()

    if "</body>" in html:
        return html.replace("</body>", assets + "\n</body>", 1)

    return html + "\n" + assets


try:
    _ptp113b3151a_original_create_mobile_app_v1 = create_mobile_app

    def create_mobile_app(*args, **kwargs):  # type: ignore[no-redef]
        app = _ptp113b3151a_original_create_mobile_app_v1(*args, **kwargs)

        if not getattr(app, "_ptp113b3151a_currency_controls_v1", False):
            @app.after_request
            def _ptp113b3151a_currency_after_request_v1(response):
                try:
                    if request.path == "/session/setup":
                        content_type = str(response.headers.get("Content-Type", ""))
                        if "text/html" in content_type:
                            html = response.get_data(as_text=True)
                            html = _ptp113b3151a_inject_currency_controls_v1(html)
                            response.set_data(html)
                            response.headers["Content-Length"] = str(len(response.get_data()))
                    return response
                except Exception as exc:
                    response.headers["X-PTP113B3151A-Currency-Warning"] = str(exc)[:120]
                    return response

            app._ptp113b3151a_currency_controls_v1 = True

        return app
except NameError:
    pass



# PTP-113B.3.1A.5.1A.1_CURRENCY_LAYOUT_RECOVERY_LOGIC_V1
def _ptp113b3151a1_currency_layout_assets_v1():
    return """
<style id="ptp113b3151a1-currency-layout-style">
  input[type=number]::-webkit-outer-spin-button,
  input[type=number]::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  input[type=number] {
    -moz-appearance: textfield;
  }

  .money-stepper {
    display: grid !important;
    grid-template-columns: 42px minmax(0, 1fr) 42px !important;
    gap: 8px !important;
    align-items: center !important;
    width: 100% !important;
    margin: 6px 0 8px 0 !important;
  }

  .money-stepper button {
    width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    border-radius: 10px !important;
    border: 1px solid #31516f !important;
    background: #102239 !important;
    color: #f5c542 !important;
    font-size: 22px !important;
    line-height: 1 !important;
    font-weight: 800 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
  }

  .money-stepper input {
    width: 100% !important;
    height: 42px !important;
    min-height: 42px !important;
    border-radius: 10px !important;
    border: 1px solid #31516f !important;
    background: #061423 !important;
    color: #ffffff !important;
    padding: 0 12px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    box-sizing: border-box !important;
  }

  .money-hidden-source {
    display: none !important;
  }

  .money-help {
    color: #8ea4b9 !important;
    font-size: 11px !important;
    line-height: 1.35 !important;
    margin: 0 0 12px 0 !important;
  }

  .money-recovery-limit-hidden {
    display: none !important;
  }
</style>

<script id="ptp113b3151a1-currency-layout-script">
(function () {
  const LABEL_TARGETS = [
    "Banca simulada inicial",
    "Valor da entrada simulada",
    "Lucro desejado da sessão",
    "Limite máximo de entrada simulada"
  ];

  function parseMoney(value) {
    // PTP-113B.3.1A.5.1A.8_NORMALIZE_PARSE_BRL
    if (value === null || value === undefined) return 0;

    let text = String(value).trim();
    if (!text) return 0;

    text = text
      .replace(/\u00A0/g, " ")
      .replace(/[^\d,.\-]/g, "")
      .trim();

    if (!text) return 0;

    const negative = text.indexOf("-") !== -1;
    text = text.replace(/-/g, "");

    const hasComma = text.indexOf(",") !== -1;
    const hasDot = text.indexOf(".") !== -1;
    let normalized = text;

    if (hasComma && hasDot) {
      const lastComma = text.lastIndexOf(",");
      const lastDot = text.lastIndexOf(".");

      if (lastComma > lastDot) {
        // Padrão BR: 1.234,56
        normalized = text.replace(/\./g, "").replace(",", ".");
      } else {
        // Padrão internacional: 1,234.56
        normalized = text.replace(/,/g, "");
      }
    } else if (hasComma) {
      const parts = text.split(",");

      if (parts.length > 2) {
        const cents = parts.pop();
        normalized = parts.join("") + "." + cents;
      } else {
        const whole = parts[0] || "0";
        const cents = parts[1] || "";

        if (cents.length === 0) {
          normalized = whole;
        } else if (cents.length <= 2) {
          normalized = whole + "." + cents;
        } else {
          // Caso raro: 1,000 tratado como milhar.
          normalized = whole + cents;
        }
      }
    } else if (hasDot) {
      const parts = text.split(".");

      if (parts.length > 2) {
        const last = parts[parts.length - 1] || "";

        if (last.length <= 2) {
          normalized = parts.slice(0, -1).join("") + "." + last;
        } else {
          normalized = parts.join("");
        }
      } else {
        const whole = parts[0] || "0";
        const tail = parts[1] || "";

        if (tail.length === 0) {
          normalized = whole;
        } else if (tail.length <= 2) {
          normalized = whole + "." + tail;
        } else {
          // Caso BR com ponto de milhar: 1.000
          normalized = whole + tail;
        }
      }
    }

    let number = Number.parseFloat(normalized);
    if (!Number.isFinite(number)) return 0;

    if (negative) number = -number;

    return Math.round(number * 100) / 100;
  }

  function toDecimal(value) {
    return Number(value || 0).toFixed(2);
  }

  function formatBRL(value) {
    return Number(value || 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function normalizeText(text) {
    return String(text || "").replace(/\\s+/g, " ").trim().toLowerCase();
  }

  function findInputAfterLabel(label) {
    let node = label.nextElementSibling;
    let guard = 0;
    while (node && guard < 8) {
      if (node.matches && node.matches("input")) return node;
      const nested = node.querySelector ? node.querySelector("input") : null;
      if (nested) return nested;
      node = node.nextElementSibling;
      guard += 1;
    }
    return null;
  }

  function fieldNameForLabel(labelText, source) {
    const t = normalizeText(labelText);
    if (t.includes("banca simulada inicial")) return "initial_bankroll";
    if (t.includes("valor da entrada simulada")) return "initial_entry";
    if (t.includes("lucro desejado")) return "profit_target";
    if (t.includes("limite máximo de entrada")) return "max_entry_limit";
    return source.name || source.id || "money";
  }

  function createMoneyControl(source, labelText) {
    if (!source || source.dataset.moneyFieldV2 === "1") return;

    const fieldName = fieldNameForLabel(labelText, source);
    source.dataset.moneyFieldV2 = "1";
    source.dataset.moneySemanticName = fieldName;
    source.classList.add("money-hidden-source");
    source.setAttribute("step", "1.00");

    const initialValue = parseMoney(source.value || source.getAttribute("value") || "0");
    source.value = toDecimal(initialValue);

    const wrapper = document.createElement("div");
    wrapper.className = "money-stepper";
    wrapper.dataset.moneyStepperFor = fieldName;

    const minus = document.createElement("button");
    minus.type = "button";
    minus.textContent = "−";
    minus.setAttribute("aria-label", "Diminuir R$ 1,00");

    const visible = document.createElement("input");
    visible.type = "text";
    visible.inputMode = "decimal";
    visible.autocomplete = "off";
    visible.value = formatBRL(initialValue);
    visible.setAttribute("aria-label", labelText + " em reais");

    const plus = document.createElement("button");
    plus.type = "button";
    plus.textContent = "+";
    plus.setAttribute("aria-label", "Aumentar R$ 1,00");

    function sync(value) {
      const min = parseMoney(source.getAttribute("min") || "0");
      let next = Number(value || 0);
      if (!Number.isFinite(next)) next = 0;
      if (next < min) next = min;

      source.value = toDecimal(next);
      visible.value = formatBRL(next);

      source.dispatchEvent(new Event("input", { bubbles: true }));
      source.dispatchEvent(new Event("change", { bubbles: true }));
    }

    minus.addEventListener("click", function () {
      sync(parseMoney(source.value) - 1);
    });

    plus.addEventListener("click", function () {
      sync(parseMoney(source.value) + 1);
    });

    visible.addEventListener("focus", function () {
      visible.value = toDecimal(parseMoney(source.value)).replace(".", ",");
      visible.select();
    });

    visible.addEventListener("blur", function () {
      sync(parseMoney(visible.value));
    });

    visible.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        sync(parseMoney(visible.value));
        visible.blur();
      }
    });

    wrapper.appendChild(minus);
    wrapper.appendChild(visible);
    wrapper.appendChild(plus);

    source.parentNode.insertBefore(wrapper, source.nextSibling);

    const help = document.createElement("div");
    help.className = "money-help";
    help.textContent = "Ajuste em R$ 1,00 por clique. Valor enviado ao contrato como decimal monetário.";
    wrapper.parentNode.insertBefore(help, wrapper.nextSibling);
  }

  function applyByLabels() {
    const labels = Array.from(document.querySelectorAll("label"));
    labels.forEach(function (label) {
      const text = normalizeText(label.textContent);
      const match = LABEL_TARGETS.find(function (target) {
        return text.includes(normalizeText(target));
      });
      if (!match) return;

      const input = findInputAfterLabel(label);
      if (!input) return;

      createMoneyControl(input, match);
    });
  }

  function getRecoverySelect() {
    return document.querySelector('[name="recovery_mode"]');
  }

  function findRecoveryLimitElements() {
    const result = {
      label: null,
      source: document.querySelector('[data-money-semantic-name="max_entry_limit"], [name="max_entry_limit"], #max_entry_limit'),
      stepper: null,
      help: null
    };

    const labels = Array.from(document.querySelectorAll("label"));
    result.label = labels.find(function (label) {
      return normalizeText(label.textContent).includes("limite máximo de entrada");
    }) || null;

    if (result.source) {
      result.stepper = document.querySelector('[data-money-stepper-for="max_entry_limit"]');
      if (result.stepper && result.stepper.nextElementSibling && result.stepper.nextElementSibling.classList.contains("money-help")) {
        result.help = result.stepper.nextElementSibling;
      }
    }

    return result;
  }

  function updateRecoveryLimitVisibility() {
    const select = getRecoverySelect();
    const mode = select ? String(select.value || "NONE").toUpperCase() : "NONE";
    const hidden = mode === "NONE" || mode === "SEM_RECUPERACAO" || mode === "SEM_RECUPERAÇÃO";

    const elements = findRecoveryLimitElements();

    [elements.label, elements.stepper, elements.help].forEach(function (el) {
      if (!el) return;
      el.classList.toggle("money-recovery-limit-hidden", hidden);
    });

    if (elements.source) {
      if (hidden) {
        elements.source.dataset.previousMoneyValue = elements.source.value || "";
        elements.source.value = "";
        elements.source.disabled = true;
      } else {
        elements.source.disabled = false;
        if (!elements.source.value) {
          elements.source.value = elements.source.dataset.previousMoneyValue || "20.00";
        }
      }
    }
  }

  function applyMoneyUI() {
    applyByLabels();
    updateRecoveryLimitVisibility();

    const select = getRecoverySelect();
    if (select && select.dataset.moneyRecoveryListener !== "1") {
      select.dataset.moneyRecoveryListener = "1";
      select.addEventListener("change", updateRecoveryLimitVisibility);
      select.addEventListener("input", updateRecoveryLimitVisibility);
    }
  }

  document.addEventListener("DOMContentLoaded", applyMoneyUI);
  setTimeout(applyMoneyUI, 100);
  setTimeout(applyMoneyUI, 500);

  document.addEventListener("submit", function () {
    updateRecoveryLimitVisibility();

    document.querySelectorAll("[data-money-field-v2='1']").forEach(function (source) {
      if (source.disabled) return;
      source.value = toDecimal(parseMoney(source.value));
    });
  }, true);

  window.PTP113B3151A1_CURRENCY_LAYOUT_RECOVERY_LOGIC = true;
})();
</script>
"""

def _ptp113b3151a1_inject_currency_layout_v1(html):
    if not isinstance(html, str):
        return html

    if "PTP113B3151A1_CURRENCY_LAYOUT_RECOVERY_LOGIC" in html:
        return html

    assets = _ptp113b3151a1_currency_layout_assets_v1()

    if "</body>" in html:
        return html.replace("</body>", assets + "\n</body>", 1)

    return html + "\n" + assets


try:
    _ptp113b3151a1_original_create_mobile_app_v1 = create_mobile_app

    def create_mobile_app(*args, **kwargs):  # type: ignore[no-redef]
        app = _ptp113b3151a1_original_create_mobile_app_v1(*args, **kwargs)

        if not getattr(app, "_ptp113b3151a1_currency_layout_v1", False):
            @app.after_request
            def _ptp113b3151a1_currency_layout_after_request_v1(response):
                try:
                    if request.path == "/session/setup":
                        content_type = str(response.headers.get("Content-Type", ""))
                        if "text/html" in content_type:
                            html = response.get_data(as_text=True)
                            html = _ptp113b3151a1_inject_currency_layout_v1(html)
                            response.set_data(html)
                            response.headers["Content-Length"] = str(len(response.get_data()))
                    return response
                except Exception as exc:
                    response.headers["X-PTP113B3151A1-CurrencyLayout-Warning"] = str(exc)[:120]
                    return response

            app._ptp113b3151a1_currency_layout_v1 = True

        return app
except NameError:
    pass



# PTP-113B.3.1A.5.1A.6_FIX_STEPPER_GUARD
def _ptp113b3151a51a6_disable_legacy_currency_controls_brl():
    """
    Desativa a injeção monetária legada V1 sem usar app global.

    Motivo:
    - A auditoria encontrou dois blocos monetários em /session/setup.
    - O bloco legado V1 injeta parseMoney/formatBRL duplicados.
    - A correção anterior usou @app.after_request fora de create_mobile_app e quebrou import.

    Estratégia segura:
    - Não remove fisicamente o código antigo.
    - Substitui apenas funções legadas que carregam o marcador exato
      PTP113B3151A_CURRENCY_CONTROLS_BRL.
    - Mantém o bloco mais novo PTP113B3151A1_CURRENCY_LAYOUT_RECOVERY_LOGIC.
    """
    legacy_marker = "PTP113B3151A_CURRENCY_CONTROLS_BRL"
    disabled = []

    def _noop_html(html, *args, **kwargs):
        return html

    def _noop_assets(*args, **kwargs):
        return ""

    try:
        import inspect as _inspect

        for _name, _obj in list(globals().items()):
            if not callable(_obj):
                continue

            if not _name.startswith("_ptp113b3151a"):
                continue

            if _name.startswith("_ptp113b3151a1"):
                continue

            if _name.startswith("_ptp113b3151a51a6"):
                continue

            try:
                _source = _inspect.getsource(_obj)
            except Exception:
                _source = ""

            if legacy_marker not in _source:
                continue

            if "inject" in _name:
                globals()[_name] = _noop_html
                disabled.append(_name)
                continue

            if "asset" in _name or "assets" in _name:
                globals()[_name] = _noop_assets
                disabled.append(_name)
                continue

        globals()["_PTP113B3151A51A6_DISABLED_LEGACY_CURRENCY_CONTROLS"] = tuple(disabled)

    except Exception as _exc:
        globals()["_PTP113B3151A51A6_DISABLED_LEGACY_CURRENCY_CONTROLS_ERROR"] = str(_exc)[:200]


_ptp113b3151a51a6_disable_legacy_currency_controls_brl()


if __name__ == "__main__":
    raise SystemExit(main())
