from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from statistics import mean
import tkinter as tk


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "runtime"
LAST_FILE = RUNTIME / "last_live_reading.json"
HISTORY_FILE = RUNTIME / "live_price_history.json"
TIMING_FILE = RUNTIME / "live_timing_profile.json"

BG = "#061018"
PANEL = "#0d1b2a"
PANEL_2 = "#10263a"
TEXT = "#e8f6ff"
MUTED = "#8aa4b8"
CYAN = "#23d6ff"
GREEN = "#21e08a"
RED = "#ff4d5e"
AMBER = "#ffbf3c"
GRAY = "#5c6f80"


def parse_args():
    parser = argparse.ArgumentParser(description="PTP-107C Futuristic Live Popup + Smart Signal Simulator")
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--interval", type=float, default=8)
    parser.add_argument("--clear-runtime", action="store_true")
    parser.add_argument("--no-runner", action="store_true")
    return parser.parse_args()


def safe_read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return default
        return json.loads(text)
    except Exception:
        return default


def to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("R$", "").replace("%", "").replace(" ", "")
    text = re.sub(r"[^\d,.\-]", "", text)

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def deep_get(obj, keys):
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]

        for value in obj.values():
            found = deep_get(value, keys)
            if found not in (None, ""):
                return found

    if isinstance(obj, list):
        for item in obj:
            found = deep_get(item, keys)
            if found not in (None, ""):
                return found

    return None


def extract_asset_from_title(title):
    text = str(title or "")

    if re.search(r"cafe[ií]na\s+index", text, re.IGNORECASE):
        return "Cafeina Index"

    if re.search(r"latam\s+index", text, re.IGNORECASE):
        return "LATAM Index"

    return None


def normalize_asset(asset, title):
    raw = str(asset or "").strip()
    extracted = extract_asset_from_title(title)

    if raw.upper() in ("", "UNKNOWN", "DATA", "N/A", "NONE", "-"):
        return extracted or "UNKNOWN"

    if re.search(r"cafe[ií]na\s+index", raw, re.IGNORECASE):
        return "Cafeina Index"

    return raw


def iter_records(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from iter_records(item)
        return

    if isinstance(obj, dict):
        used = False
        for key in ("history", "prices", "readings", "records", "items", "data"):
            if key in obj:
                used = True
                yield from iter_records(obj[key])
        if not used:
            yield obj
        return

    yield obj


def extract_prices(history_obj):
    prices = []

    for item in iter_records(history_obj):
        if isinstance(item, (int, float, str)):
            price = to_float(item)
        else:
            price = to_float(
                deep_get(
                    item,
                    [
                        "price",
                        "current_price",
                        "last_price",
                        "value",
                        "quote",
                        "live_price",
                        "observed_price",
                    ],
                )
            )

        if price is not None and price > 0:
            prices.append(price)

    return prices[-120:]


def format_balance(raw, value):
    if raw not in (None, "", "UNKNOWN", "?"):
        return str(raw).replace("RS", "R$")
    if value is None:
        return "?"
    return f"D {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def money(value):
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def number(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def payout_text(value):
    if value is None:
        return "—"
    if value <= 1:
        value *= 100
    return f"{value:.0f}%"


def analyze(prices, current_price):
    series = list(prices)

    if current_price is not None:
        if not series or abs(series[-1] - current_price) > 0.000001:
            series.append(current_price)

    series = series[-60:]

    if len(series) < 4:
        return {
            "direction": "AGUARDANDO",
            "support": None,
            "resistance": None,
            "average": None,
            "amplitude": None,
            "signal": "AGUARDAR",
            "confidence": 20,
            "level": "baixa",
            "reason": "Histórico ainda pequeno para simular sinal com segurança.",
        }

    current = series[-1]
    support = min(series[-20:])
    resistance = max(series[-20:])
    average = mean(series)
    amplitude = resistance - support

    size = max(2, min(5, len(series) // 2))
    early = mean(series[:size])
    late = mean(series[-size:])
    delta = late - early
    threshold = max(amplitude * 0.10, abs(current) * 0.00012, 0.01)

    if delta > threshold:
        direction = "SUBINDO"
    elif delta < -threshold:
        direction = "CAINDO"
    else:
        direction = "LATERAL"

    if amplitude <= 0:
        position = 0.5
    else:
        position = (current - support) / amplitude

    near_support = position <= 0.22
    near_resistance = position >= 0.78

    signal = "AGUARDAR"
    confidence = 35
    reason = "Preço fora de zona clara de suporte ou resistência."

    if near_support and direction == "SUBINDO":
        signal = "COMPRA SIMULADA"
        confidence = 78
        reason = "Preço próximo do suporte com reação de alta no histórico curto."
    elif near_support and direction == "LATERAL":
        signal = "COMPRA SIMULADA"
        confidence = 58
        reason = "Preço próximo do suporte, mas ainda sem força direcional alta."
    elif near_resistance and direction == "CAINDO":
        signal = "VENDA SIMULADA"
        confidence = 78
        reason = "Preço próximo da resistência com reação de queda no histórico curto."
    elif near_resistance and direction == "LATERAL":
        signal = "VENDA SIMULADA"
        confidence = 58
        reason = "Preço próximo da resistência, mas ainda sem força direcional baixa."
    elif amplitude < abs(current) * 0.00025:
        signal = "AGUARDAR"
        confidence = 30
        reason = "Amplitude muito pequena. Mercado aparenta estar travado/lateral."

    level = "alta" if confidence >= 70 else "média" if confidence >= 50 else "baixa"

    return {
        "direction": direction,
        "support": support,
        "resistance": resistance,
        "average": average,
        "amplitude": amplitude,
        "signal": signal,
        "confidence": confidence,
        "level": level,
        "reason": reason,
    }


def decorate_smart_signal(smart, prices, current_price):
    support = smart.get("support")
    resistance = smart.get("resistance")
    amplitude = smart.get("amplitude")
    signal = smart.get("signal", "AGUARDAR")

    entry_price = None
    expiration = "AGUARDAR"

    if current_price is not None and support is not None and resistance is not None and amplitude is not None:
        if signal == "COMPRA SIMULADA":
            entry_price = support + (amplitude * 0.15)
            expiration = "1 min / pr?xima vela confirmada"
        elif signal == "VENDA SIMULADA":
            entry_price = resistance - (amplitude * 0.15)
            expiration = "1 min / pr?xima vela confirmada"
        else:
            entry_price = None
            expiration = "Aguardar pre?o tocar suporte/resist?ncia"

    smart["entry_price_simulated"] = entry_price
    smart["expiration_suggestion"] = expiration
    return smart


def load_state():
    last = safe_read_json(LAST_FILE, {})
    history = safe_read_json(HISTORY_FILE, [])
    timing = safe_read_json(TIMING_FILE, {})

    prices = extract_prices(history)

    title = deep_get(last, ["window_title", "title", "page_title", "browser_title"]) or ""
    asset = normalize_asset(deep_get(last, ["asset", "symbol", "active", "instrument", "market"]), title)

    price = to_float(
        deep_get(
            last,
            [
                "price",
                "current_price",
                "last_price",
                "value",
                "quote",
                "live_price",
                "observed_price",
            ],
        )
    )

    if price is None and prices:
        price = prices[-1]

    balance_raw = deep_get(last, ["balance", "saldo", "account_balance", "wallet_balance"])
    balance = to_float(balance_raw)
    payout = to_float(deep_get(last, ["payout", "profitability", "return_percent"]))
    timeframe = deep_get(last, ["timeframe", "duration", "expiration", "tempo"]) or "—"
    valid = deep_get(last, ["valid", "is_valid", "accepted"])
    reason = deep_get(last, ["reason", "validation_reason", "message", "warning"]) or "—"

    smart = decorate_smart_signal(analyze(prices, price), prices, price)

    return {
        "last": last,
        "timing": timing,
        "prices": prices,
        "asset": asset,
        "price": price,
        "balance": balance,
        "balance_raw": balance_raw,
        "payout": payout,
        "timeframe": timeframe,
        "valid": valid,
        "reason": reason,
        "smart": smart,
    }


def clear_runtime():
    RUNTIME.mkdir(parents=True, exist_ok=True)

    for path in (LAST_FILE, HISTORY_FILE, TIMING_FILE):
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


class LiveRunner:
    def __init__(self, cycles, interval, disabled=False):
        self.cycles = cycles
        self.interval = interval
        self.disabled = disabled
        self.process = None
        self.logs = []

    def start(self):
        if self.disabled:
            self.logs.append("Runner desativado por --no-runner.")
            return

        env = os.environ.copy()
        src_path = str(ROOT / "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [
            sys.executable,
            "-m",
            "predixai.main",
            "--live-loop",
            "--loop-count",
            str(self.cycles),
            "--loop-interval",
            str(self.interval),
        ]

        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                creationflags=flags,
            )
            threading.Thread(target=self._read_stdout, daemon=True).start()
            self.logs.append("Live-loop iniciado.")
        except Exception as exc:
            self.logs.append(f"Falha ao iniciar live-loop: {exc}")

    def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            line = line.strip()
            if line:
                self.logs.append(line[-180:])
                self.logs = self.logs[-8:]

    def status(self):
        if self.disabled:
            return "SEM RUNNER", GRAY

        if not self.process:
            return "INICIANDO", AMBER

        code = self.process.poll()

        if code is None:
            return "COLETANDO", GREEN

        if code == 0:
            return "FINALIZADO", CYAN

        return "ERRO LIVE-LOOP", RED

    def stop(self):
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
        except Exception:
            pass


class PopupApp:
    def __init__(self, runner):
        self.runner = runner
        self.root = tk.Tk()
        self.root.title("PredixAI Trader | PTP-107C")
        self.root.geometry("560x760+40+40")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.values = {}
        self._build()

    def _label(self, parent, text, size=10, color=TEXT, bg=PANEL, weight="normal"):
        return tk.Label(
            parent,
            text=text,
            fg=color,
            bg=bg,
            font=("Segoe UI", size, weight),
            anchor="w",
            justify="left",
        )

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=14, pady=(12, 8))

        title = tk.Label(
            header,
            text="PREDIXAI TRADER",
            fg=CYAN,
            bg=BG,
            font=("Segoe UI", 17, "bold"),
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="V1 Observador · Sinal simulado · Nenhuma ordem real",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 9),
        )
        subtitle.pack(anchor="w")

        self.status_label = tk.Label(
            self.root,
            text="INICIANDO",
            fg=AMBER,
            bg=PANEL_2,
            font=("Segoe UI", 12, "bold"),
            padx=10,
            pady=8,
        )
        self.status_label.pack(fill="x", padx=14, pady=(0, 10))

        grid = tk.Frame(self.root, bg=BG)
        grid.pack(fill="x", padx=14)

        self._card(grid, "Leituras v?lidas", "readings", 0, 0)
        self._card(grid, "Ativo", "asset", 0, 1)
        self._card(grid, "Preço", "price", 1, 0)
        self._card(grid, "Saldo", "balance", 1, 1)
        self._card(grid, "Payout", "payout", 2, 0)
        self._card(grid, "Tempo", "timeframe", 2, 1)
        self._card(grid, "Direção", "direction", 3, 0)
        self._card(grid, "Amplitude", "amplitude", 3, 1)
        self._card(grid, "Suporte", "support", 4, 0)
        self._card(grid, "Resistência", "resistance", 4, 1)

        signal_box = tk.Frame(self.root, bg=PANEL, highlightbackground=CYAN, highlightthickness=1)
        signal_box.pack(fill="x", padx=14, pady=12)

        tk.Label(
            signal_box,
            text="SINAL SIMULADO",
            fg=MUTED,
            bg=PANEL,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self.signal_label = tk.Label(
            signal_box,
            text="AGUARDAR",
            fg=AMBER,
            bg=PANEL,
            font=("Segoe UI", 19, "bold"),
        )
        self.signal_label.pack(anchor="w", padx=10, pady=(2, 2))

        self.confidence_label = tk.Label(
            signal_box,
            text="Confiança: —",
            fg=TEXT,
            bg=PANEL,
            font=("Segoe UI", 11, "bold"),
        )
        self.confidence_label.pack(anchor="w", padx=10, pady=(0, 4))

        self.reason_label = tk.Label(
            signal_box,
            text="Motivo: —",
            fg=MUTED,
            bg=PANEL,
            font=("Segoe UI", 9),
            wraplength=500,
            justify="left",
        )
        self.reason_label.pack(anchor="w", padx=10, pady=(0, 10))

        self.chart = tk.Canvas(self.root, height=130, bg="#071522", highlightthickness=1, highlightbackground="#17364d")
        self.chart.pack(fill="x", padx=14, pady=(0, 10))

        self.footer = tk.Label(
            self.root,
            text="Inicializando...",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 8),
            wraplength=510,
            justify="left",
        )
        self.footer.pack(fill="x", padx=14, pady=(0, 10))

    def _card(self, parent, title, key, row, col):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground="#16344a", highlightthickness=1)
        frame.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(frame, text=title, fg=MUTED, bg=PANEL, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=8, pady=(7, 0)
        )

        value = tk.Label(
            frame,
            text="—",
            fg=TEXT,
            bg=PANEL,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        value.pack(fill="x", padx=8, pady=(0, 7))

        self.values[key] = value

    def signal_color(self, signal):
        if signal == "COMPRA SIMULADA":
            return GREEN
        if signal == "VENDA SIMULADA":
            return RED
        return AMBER

    def draw_chart(self, prices, support, resistance):
        self.chart.delete("all")

        w = max(self.chart.winfo_width(), 500)
        h = 130
        pad = 12
        series = prices[-60:]

        if len(series) < 2:
            self.chart.create_text(
                w / 2,
                h / 2,
                text="Aguardando histórico para desenhar o mini gráfico...",
                fill=MUTED,
                font=("Segoe UI", 9),
            )
            return

        mn = min(series)
        mx = max(series)
        span = mx - mn if mx != mn else 1

        points = []
        for index, price in enumerate(series):
            x = pad + index * ((w - pad * 2) / max(1, len(series) - 1))
            y = h - pad - ((price - mn) / span) * (h - pad * 2)
            points.append((x, y))

        for i in range(1, len(points)):
            self.chart.create_line(points[i - 1], points[i], fill=CYAN, width=2)

        if support is not None:
            y = h - pad - ((support - mn) / span) * (h - pad * 2)
            self.chart.create_line(pad, y, w - pad, y, fill=GREEN, dash=(4, 3))
            self.chart.create_text(pad + 44, y - 9, text="suporte", fill=GREEN, font=("Segoe UI", 8))

        if resistance is not None:
            y = h - pad - ((resistance - mn) / span) * (h - pad * 2)
            self.chart.create_line(pad, y, w - pad, y, fill=RED, dash=(4, 3))
            self.chart.create_text(pad + 58, y + 9, text="resistência", fill=RED, font=("Segoe UI", 8))

    def refresh(self):
        state = load_state()
        smart = state["smart"]
        runner_status, runner_color = self.runner.status()

        self.status_label.config(text=runner_status, fg=runner_color)

        self.values["readings"].config(text=str(len(state["prices"])))
        self.values["asset"].config(text=state["asset"])
        self.values["price"].config(text=number(state["price"]))
        self.values["balance"].config(text=format_balance(state.get("balance_raw"), state["balance"]))
        self.values["payout"].config(text=payout_text(state["payout"]))
        self.values["timeframe"].config(text=str(state["timeframe"]))
        self.values["direction"].config(text=smart["direction"])
        self.values["amplitude"].config(text=number(smart["amplitude"]))
        self.values["support"].config(text=number(smart["support"]))
        self.values["resistance"].config(text=number(smart["resistance"]))
        self.values["entry_price"].config(text=number(smart.get("entry_price_simulated")))
        self.values["expiration_suggestion"].config(text=str(smart.get("expiration_suggestion", "?")))

        color = self.signal_color(smart["signal"])
        self.signal_label.config(text=smart["signal"], fg=color)
        self.confidence_label.config(
            text=f"Confiança: {smart['confidence']}% · {smart['level'].upper()}",
            fg=color,
        )
        self.reason_label.config(text=f"Motivo: {smart['reason']}")

        self.draw_chart(state["prices"], smart["support"], smart["resistance"])

        log = " | ".join(self.runner.logs[-2:]) if self.runner.logs else "Sem logs recentes."
        valid = state["valid"] if state["valid"] is not None else "—"
        self.footer.config(text=f"Válido: {valid} · Validação: {state['reason']} · {log}")

        self.root.after(1000, self.refresh)

    def run(self):
        self.refresh()
        self.root.mainloop()

    def close(self):
        self.runner.stop()
        self.root.destroy()


def main():
    args = parse_args()

    if args.clear_runtime:
        clear_runtime()

    runner = LiveRunner(args.cycles, args.interval, disabled=args.no_runner)
    runner.start()

    app = PopupApp(runner)
    app.run()


if __name__ == "__main__":
    main()


