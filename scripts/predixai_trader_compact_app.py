# -*- coding: utf-8 -*-
"""
PredixAI Trader Compact Launcher.

Launcher local pequeno para o painel mobile.
Nao captura tela, nao usa OCR, nao clica e nao executa ordens.
"""

from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path

import tkinter as tk


REPO = Path(__file__).resolve().parents[1]
MOBILE_PORT = 8766
BG = "#071018"
PANEL = "#101b28"
TEXT = "#f5f7fb"
MUTED = "#a8b5c6"
LINE = "#00e5ff"
GREEN = "#38d66b"
YELLOW = "#ffbf00"
RED = "#ff4d6d"


def local_ip() -> str:
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


class CompactLauncher:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("PredixAI Launcher")
        self.root.geometry("292x322")
        self.root.minsize(270, 300)
        self.root.maxsize(310, 340)
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", False)

        self.server_proc: subprocess.Popen | None = None
        self.reader_proc: subprocess.Popen | None = None
        self.mobile_url = f"http://{local_ip()}:{MOBILE_PORT}/mobile"
        self.local_url = f"http://127.0.0.1:{MOBILE_PORT}/mobile"

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        tk.Label(
            self.root,
            text="PredixAI Launcher",
            bg=BG,
            fg=LINE,
            font=("Consolas", 15, "bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        tk.Label(
            self.root,
            text="Modo observador. Não é recomendação financeira.",
            bg=BG,
            fg=YELLOW,
            font=("Arial", 8, "bold"),
            wraplength=270,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10)

        tk.Label(
            self.root,
            text="Modo observador/simulado. Não executa ordens.",
            bg=BG,
            fg=MUTED,
            font=("Arial", 8, "bold"),
            wraplength=270,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(1, 7))

        url_box = tk.Frame(self.root, bg=PANEL, highlightbackground="#24364a", highlightthickness=1)
        url_box.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            url_box,
            text="URL para o celular",
            bg=PANEL,
            fg=MUTED,
            font=("Consolas", 8),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(7, 1))

        self.url_label = tk.Label(
            url_box,
            text=self.mobile_url,
            bg=PANEL,
            fg=TEXT,
            font=("Consolas", 9, "bold"),
            wraplength=255,
            justify="left",
            anchor="w",
        )
        self.url_label.pack(fill="x", padx=8, pady=(0, 7))

        buttons = tk.Frame(self.root, bg=BG)
        buttons.pack(fill="x", padx=10)

        self._button(buttons, "Servidor mobile", self.start_mobile_server, 0, 0)
        self._button(buttons, "Abrir painel", self.open_mobile, 0, 1)
        self._button(buttons, "Leitor 3s", self.start_reader_1s, 1, 0)
        self._button(buttons, "Parar leitor", self.stop_reader, 1, 1)
        self._button(buttons, "Focar corretora", self.focus_broker, 2, 0)
        self._button(buttons, "Dashboard local", self.open_dashboard, 2, 1)

        self.status_label = tk.Label(
            self.root,
            text="Status: pronto",
            bg=BG,
            fg=MUTED,
            font=("Consolas", 8),
            wraplength=270,
            justify="left",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=10, pady=(7, 0))

        tk.Label(
            self.root,
            text="SEM CLIQUE / SEM ORDEM / SEM CONTA REAL",
            bg=BG,
            fg=MUTED,
            font=("Consolas", 7),
        ).pack(side="bottom", pady=(0, 6))

    def _button(self, parent: tk.Frame, text: str, command, row: int, col: int) -> None:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg="#13263a",
            fg=TEXT,
            activebackground="#1d3a58",
            activeforeground=TEXT,
            relief="flat",
            font=("Arial", 8, "bold"),
            height=2,
        )
        button.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
        parent.grid_columnconfigure(col, weight=1)

    def run(self) -> None:
        self.root.mainloop()

    def start_mobile_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self._status("Servidor mobile já está rodando.", GREEN)
            return

        script = REPO / "scripts" / "predixai_trader_mobile_server.py"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.server_proc = subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(REPO),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            self._status(f"Servidor mobile iniciado: {self.mobile_url}", GREEN)
        except Exception as exc:
            self._status(f"Falha ao iniciar servidor: {exc}", RED)

    def open_mobile(self) -> None:
        webbrowser.open(self.local_url)
        self._status("Painel mobile aberto no navegador local.", GREEN)

    def start_reader_1s(self) -> None:
        if self._post_mobile("/api/mobile/start?interval=3"):
            self._status("Leitor 3s iniciado pelo servidor mobile.", GREEN)
            return

        if self.reader_proc and self.reader_proc.poll() is None:
            self._status("Leitor já está rodando.", GREEN)
            return

        python_exe = REPO / ".venv" / "Scripts" / "python.exe"
        if not python_exe.exists():
            python_exe = Path(sys.executable)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.reader_proc = subprocess.Popen(
                [
                    str(python_exe),
                    "-m",
                    "predixai.main",
                    "--live-loop",
                    "--price-only",
                    "--loop-count",
                    "9999",
                    "--loop-interval",
                    "3",
                ],
                cwd=str(REPO),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            self._status("Leitor 3s iniciado localmente em modo price-only.", GREEN)
        except Exception as exc:
            self._status(f"Falha ao iniciar leitor: {exc}", RED)

    def stop_reader(self) -> None:
        stopped = self._post_mobile("/api/mobile/stop")
        local_stopped = False
        if self.reader_proc and self.reader_proc.poll() is None:
            self._kill_process(self.reader_proc)
            self.reader_proc = None
            local_stopped = True
        if stopped or local_stopped:
            self._status("Leitor parado.", YELLOW)
        else:
            self._status("Nenhum leitor controlado pelo launcher.", MUTED)

    def open_dashboard(self) -> None:
        webbrowser.open("http://127.0.0.1:8765")
        self._status("Dashboard local aberto.", GREEN)

    def focus_broker(self) -> None:
        if os.name != "nt":
            self._status("Focar corretora automático só está disponível no Windows.", YELLOW)
            return

        try:
            user32 = ctypes.windll.user32
            target = {"hwnd": 0, "title": ""}

            def callback(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                lowered = title.lower()
                valid = (
                    ("olymp" in lowered or "olymptrade" in lowered)
                    and ("index" in lowered or "cafe" in lowered or "asia composite" in lowered)
                )
                if valid:
                    target["hwnd"] = hwnd
                    target["title"] = title
                    return False
                return True

            user32.EnumWindows(
                ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback),
                0,
            )
            if not target["hwnd"]:
                self._status("Janela da corretora não encontrada.", YELLOW)
                return
            user32.ShowWindow(target["hwnd"], 9)
            user32.SetForegroundWindow(target["hwnd"])
            self._status(f"Corretora focada: {target['title'][:42]}", GREEN)
        except Exception as exc:
            self._status(f"Falha ao focar corretora: {exc}", RED)

    def _post_mobile(self, path: str) -> bool:
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{MOBILE_PORT}{path}",
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=1.5) as response:
                return 200 <= response.status < 300
        except Exception:
            return False

    def _kill_process(self, process: subprocess.Popen) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()

    def _status(self, text: str, color: str = MUTED) -> None:
        self.status_label.config(text=f"Status: {text}", fg=color)

    def _on_close(self) -> None:
        self.root.destroy()


if __name__ == "__main__":
    CompactLauncher().run()
