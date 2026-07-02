from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from statistics import mean
import tkinter as tk


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RUNTIME = ROOT / "data" / "runtime"
LAST = RUNTIME / "last_live_reading.json"
HISTORY = RUNTIME / "live_price_history.json"

BG = "#050b14"
PANEL = "#0b1d30"
PANEL2 = "#102a43"
TEXT = "#eaf7ff"
MUTED = "#8ca9bd"
CYAN = "#19d7ff"
GREEN = "#22e089"
RED = "#ff4f63"
AMBER = "#ffc247"


def read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def to_float(value):
    if value in (None, "", "UNKNOWN", "—"):
        return None
    text = str(value).replace("R$", "").replace("D", "").replace("%", "").strip()
    text = text.replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None


def title_price(title):
    text = str(title or "")
    match = re.search(r"([0-9]{3,6}[.,][0-9]{1,6})\s+[A-Za-zÀ-ÿ ]{2,40}Index", text, re.I)
    if match:
        return to_float(match.group(1))
    match = re.search(r"\b([0-9]{3,6}[.,][0-9]{1,6})\b", text)
    return to_float(match.group(1)) if match else None


def fmt(value):
    if value in (None, "", "UNKNOWN"):
        return "—"
    return str(value)


def fmt_num(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def extract_prices(history, anchor=None):
    raw = []
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            price = to_float(item.get("price_value")) or to_float(item.get("price"))
            if price:
                raw.append(price)

    if anchor and anchor > 1000:
        low = anchor * 0.995
        high = anchor * 1.005
        filtered = [p for p in raw if low <= p <= high]
        return filtered[-80:]

    return [p for p in raw if p > 1000][-80:]


def detect_result(text):
    t = str(text or "")
    if re.search(r"\+\s*(?:D|R\$)?\s*\d", t):
        return "WIN ESTIMADO"
    if re.search(r"-\s*(?:D|R\$)?\s*\d", t):
        return "LOSS ESTIMADO"
    return "DESCONHECIDO"


def analyze(prices, current_price):
    series = list(prices)
    if current_price and current_price > 1000:
        if not series or abs(series[-1] - current_price) > 0.01:
            series.append(current_price)

    series = series[-60:]

    if len(series) < 5:
        return {
            "signal": "AGUARDAR",
            "state": "COLETANDO DADOS",
            "confidence": 20,
            "direction": "AGUARDANDO",
            "support": None,
            "resistance": None,
            "amplitude": None,
            "trigger": None,
            "expiration": "Aguardar",
            "instruction": "Aguardar pelo menos 5 leituras válidas.",
            "reason": "Histórico ainda pequeno.",
            "block": "Não simular entrada ainda.",
        }

    current = series[-1]
    window = series[-20:]
    support = min(window)
    resistance = max(window)
    amplitude = resistance - support
    avg = mean(window)

    early = mean(series[-8:-4]) if len(series) >= 8 else mean(series[:2])
    late = mean(series[-4:])
    delta = late - early
    threshold = max(amplitude * 0.12, current * 0.00008)

    if delta > threshold:
        direction = "SUBINDO"
    elif delta < -threshold:
        direction = "CAINDO"
    else:
        direction = "LATERAL"

    position = 0.5 if amplitude <= 0 else (current - support) / amplitude
    near_support = position <= 0.22
    near_resistance = position >= 0.78

    signal = "AGUARDAR"
    confidence = 35
    trigger = None
    expiration = "Aguardar suporte/resistência"
    state = "AGUARDAR CONFIRMAÇÃO"
    instruction = "Não simular entrada agora."
    reason = "Preço fora de zona clara."
    block = "Aguardar preço chegar em suporte ou resistência."

    if near_support and direction in ("SUBINDO", "LATERAL"):
        signal = "COMPRA SIMULADA"
        confidence = 72 if direction == "SUBINDO" else 58
        trigger = support + amplitude * 0.15
        expiration = "1 min / próxima vela"
        state = "PRONTO PARA SIMULAR" if confidence >= 70 else "SINAL MÉDIO"
        instruction = f"Simular compra somente se o preço tocar {fmt_num(trigger)} e reagir para cima."
        reason = "Preço próximo do suporte com possível reação."
        block = "Cancelar simulação se romper abaixo do suporte."
    elif near_resistance and direction in ("CAINDO", "LATERAL"):
        signal = "VENDA SIMULADA"
        confidence = 72 if direction == "CAINDO" else 58
        trigger = resistance - amplitude * 0.15
        expiration = "1 min / próxima vela"
        state = "PRONTO PARA SIMULAR" if confidence >= 70 else "SINAL MÉDIO"
        instruction = f"Simular venda somente se o preço tocar {fmt_num(trigger)} e rejeitar para baixo."
        reason = "Preço próximo da resistência com possível rejeição."
        block = "Cancelar simulação se romper acima da resistência."
    elif amplitude < current * 0.0002:
        confidence = 25
        reason = "Amplitude pequena. Mercado travado."
        block = "Evitar simulação em lateralidade estreita."

    return {
        "signal": signal,
        "state": state,
        "confidence": confidence,
        "direction": direction,
        "support": support,
        "resistance": resistance,
        "amplitude": amplitude,
        "trigger": trigger,
        "expiration": expiration,
        "instruction": instruction,
        "reason": reason,
        "block": block,
    }


class App:
    def __init__(self):
        self.reader = None
        self.dashboard = None
        self.logs = []

        self.root = tk.Tk()
        self.root.title("PredixAI Trader Smart App")
        self.root.geometry("900x680+30+20")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.values = {}
        self.build()
        self.refresh()

    def build(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(top, text="PREDIXAI TRADER", fg=CYAN, bg=BG, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(top, text="V1 Observador · sinal simulado · sem ordem real", fg=MUTED, bg=BG, font=("Segoe UI", 10)).pack(anchor="w")

        self.status = tk.Label(self.root, text="PARADO", fg=AMBER, bg=PANEL2, font=("Segoe UI", 13, "bold"), pady=9)
        self.status.pack(fill="x", padx=16, pady=6)

        btns = tk.Frame(self.root, bg=BG)
        btns.pack(fill="x", padx=16)

        self.button(btns, "Abrir corretora", self.open_broker, 0, 0)
        self.button(btns, "Iniciar 3s", lambda: self.start(3), 0, 1)
        self.button(btns, "Iniciar 5s", lambda: self.start(5), 0, 2)
        self.button(btns, "Parar", self.stop_reader, 0, 3)
        self.button(btns, "Dashboard", self.open_dashboard, 0, 4)
        self.button(btns, "Limpar", self.clear_runtime, 0, 5)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        mid = tk.Frame(body, bg=BG)
        mid.grid(row=0, column=1, sticky="nsew", padx=8)
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=2)

        self.section(left, "DADOS AO VIVO")
        for title, key in [
            ("Ativo", "asset"),
            ("Preço atual", "price"),
            ("Payout", "payout"),
            ("Saldo OCR", "balance"),
            ("Valor entrada OCR", "trade_value"),
            ("Duração", "duration"),
            ("Leituras válidas", "count"),
            ("Resultado detectado", "result"),
        ]:
            self.card(left, title, key)

        self.section(mid, "ANÁLISE")
        for title, key in [
            ("Direção", "direction"),
            ("Suporte", "support"),
            ("Resistência", "resistance"),
            ("Amplitude", "amplitude"),
            ("Confiança", "confidence"),
            ("Estado", "state"),
        ]:
            self.card(mid, title, key)

        self.chart = tk.Canvas(mid, height=125, bg="#071522", highlightbackground="#1c405f", highlightthickness=1)
        self.chart.pack(fill="x", pady=6)

        self.section(right, "INSTRUÇÃO DO ROBÔ")
        self.signal = tk.Label(right, text="AGUARDAR", fg=AMBER, bg=PANEL, font=("Segoe UI", 28, "bold"), pady=12)
        self.signal.pack(fill="x", pady=(0, 8))

        for title, key in [
            ("Gatilho simulado", "trigger"),
            ("Expiração simulada", "expiration"),
            ("Instrução", "instruction"),
            ("Motivo técnico", "reason"),
            ("Bloqueio", "block"),
        ]:
            self.big_card(right, title, key)

        self.log = tk.Label(self.root, text="Pronto.", fg=MUTED, bg=BG, font=("Consolas", 8), justify="left", wraplength=850)
        self.log.pack(fill="x", padx=16, pady=(0, 8))

    def section(self, parent, text):
        tk.Label(parent, text=text, fg=CYAN, bg=BG, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))

    def button(self, parent, text, command, row, col):
        b = tk.Button(parent, text=text, command=command, fg=TEXT, bg="#102a43", activebackground="#17405f", activeforeground=TEXT, font=("Segoe UI", 9, "bold"), relief="flat", pady=8)
        b.grid(row=row, column=col, sticky="ew", padx=3)
        parent.grid_columnconfigure(col, weight=1)

    def card(self, parent, title, key):
        f = tk.Frame(parent, bg=PANEL, highlightbackground="#193955", highlightthickness=1)
        f.pack(fill="x", pady=4)
        tk.Label(f, text=title, fg=MUTED, bg=PANEL, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        v = tk.Label(f, text="—", fg=TEXT, bg=PANEL, font=("Segoe UI", 11, "bold"), wraplength=170, justify="left")
        v.pack(anchor="w", padx=8, pady=(0, 7))
        self.values[key] = v

    def big_card(self, parent, title, key):
        f = tk.Frame(parent, bg=PANEL, highlightbackground="#193955", highlightthickness=1)
        f.pack(fill="x", pady=4)
        tk.Label(f, text=title, fg=MUTED, bg=PANEL, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(7, 0))
        v = tk.Label(f, text="—", fg=TEXT, bg=PANEL, font=("Segoe UI", 12, "bold"), wraplength=330, justify="left")
        v.pack(anchor="w", padx=10, pady=(0, 8))
        self.values[key] = v

    def open_broker(self):
        webbrowser.open("https://olymptrade.com/platform")
        self.logs.append("Corretora aberta. Use apenas demo/observador.")

    def open_dashboard(self):
        if not self.dashboard or self.dashboard.poll() is not None:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.dashboard = subprocess.Popen(
                [sys.executable, "-m", "predixai.main", "--dashboard"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            time.sleep(1)
        webbrowser.open("http://127.0.0.1:8765")
        self.logs.append("Dashboard iniciado/aberto.")

    def clear_runtime(self):
        RUNTIME.mkdir(parents=True, exist_ok=True)
        for p in RUNTIME.glob("*.json"):
            try:
                p.unlink()
            except Exception:
                pass
        self.logs.append("Runtime limpo.")

    def start(self, interval):
        if self.reader and self.reader.poll() is None:
            self.logs.append("Leitura já está rodando.")
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

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

        self.status.config(text=f"RODANDO · {interval}s", fg=GREEN)
        self.logs.append("Iniciando leitura. O app será minimizado para o OCR focar na corretora.")

        def launch():
            self.reader = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=flags)
            threading.Thread(target=self.read_logs, daemon=True).start()

        self.root.after(700, self.root.iconify)
        self.root.after(1500, launch)

    def read_logs(self):
        if not self.reader or not self.reader.stdout:
            return
        for line in self.reader.stdout:
            line = line.strip()
            if line:
                self.logs.append(line[-180:])
                self.logs = self.logs[-6:]

    def stop_reader(self):
        if self.reader and self.reader.poll() is None:
            self.reader.terminate()
        self.status.config(text="PARADO", fg=AMBER)
        self.logs.append("Leitura parada.")

    def draw_chart(self, prices):
        self.chart.delete("all")
        w = max(self.chart.winfo_width(), 260)
        h = 125
        pad = 10

        if len(prices) < 2:
            self.chart.create_text(w / 2, h / 2, text="Aguardando histórico...", fill=MUTED)
            return

        series = prices[-50:]
        mn, mx = min(series), max(series)
        span = mx - mn if mx != mn else 1
        pts = []

        for i, p in enumerate(series):
            x = pad + i * ((w - pad * 2) / max(1, len(series) - 1))
            y = h - pad - ((p - mn) / span) * (h - pad * 2)
            pts.append((x, y))

        for i in range(1, len(pts)):
            self.chart.create_line(pts[i - 1], pts[i], fill=CYAN, width=2)

    def refresh(self):
        last = read_json(LAST, {})
        history = read_json(HISTORY, [])

        current = title_price(last.get("window_title")) or to_float(last.get("price"))
        prices = extract_prices(history, current)
        smart = analyze(prices, current)

        source_text = last.get("source_ocr_text", "")
        result = detect_result(source_text)

        signal_color = AMBER
        if smart["signal"] == "COMPRA SIMULADA":
            signal_color = GREEN
        elif smart["signal"] == "VENDA SIMULADA":
            signal_color = RED

        self.values["asset"].config(text=fmt(last.get("asset")))
        self.values["price"].config(text=fmt_num(current))
        self.values["payout"].config(text=fmt(last.get("payout")))
        self.values["balance"].config(text=fmt(last.get("balance")))
        self.values["trade_value"].config(text=fmt(last.get("trade_value")))
        self.values["duration"].config(text=fmt(last.get("duration")))
        self.values["count"].config(text=str(len(prices)))
        self.values["result"].config(text=result)

        self.values["direction"].config(text=smart["direction"])
        self.values["support"].config(text=fmt_num(smart["support"]))
        self.values["resistance"].config(text=fmt_num(smart["resistance"]))
        self.values["amplitude"].config(text=fmt_num(smart["amplitude"]))
        self.values["confidence"].config(text=f'{smart["confidence"]}%')
        self.values["state"].config(text=smart["state"])

        self.signal.config(text=smart["signal"], fg=signal_color)
        self.values["trigger"].config(text=fmt_num(smart["trigger"]))
        self.values["expiration"].config(text=smart["expiration"])
        self.values["instruction"].config(text=smart["instruction"])
        self.values["reason"].config(text=smart["reason"])
        self.values["block"].config(text=smart["block"])

        self.draw_chart(prices)

        if self.reader and self.reader.poll() is not None and self.status.cget("text").startswith("RODANDO"):
            self.status.config(text="FINALIZADO", fg=AMBER)

        self.log.config(text="\n".join(self.logs[-6:]) or "Pronto.")
        self.root.after(1000, self.refresh)

    def close(self):
        self.stop_reader()
        if self.dashboard and self.dashboard.poll() is None:
            self.dashboard.terminate()
        self.root.destroy()


if __name__ == "__main__":
    App().root.mainloop()
