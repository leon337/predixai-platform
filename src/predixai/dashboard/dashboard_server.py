"""Local dashboard server for PredixAI BR."""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Serve the PredixAI dashboard shell and last live reading."""

    root = Path(__file__).resolve().parent
    project_root = Path(__file__).resolve().parents[3]

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send_file(self.root / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if self.path == "/static/style.css":
            self._send_file(self.root / "static" / "style.css", "text/css; charset=utf-8")
            return

        if self.path == "/static/app.js":
            self._send_file(self.root / "static" / "app.js", "application/javascript; charset=utf-8")
            return

        if self.path == "/api/last-reading":
            self._send_json(self._load_last_reading())
            return

        self.send_error(404, "Dashboard resource not found.")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404, "Dashboard file not found.")
            return

        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, data: dict[str, object]) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _load_last_reading(self) -> dict[str, object]:
        reading_path = self.project_root / "captures" / "live_once_fields" / "calibration_result.json"

        if not reading_path.exists():
            return {
                "status": "WAITING",
                "message": "Nenhuma leitura live-once encontrada.",
                "asset": "Aguardando leitura",
                "price": "Aguardando leitura",
                "payout": "Aguardando leitura",
                "balance": "Aguardando leitura",
                "trade_value": "Aguardando leitura",
                "duration": "Aguardando leitura",
                "unknown_fields": [],
            }

        try:
            data = json.loads(reading_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "status": "ERROR",
                "message": f"Falha ao ler ultima leitura: {exc}",
                "asset": "Erro",
                "price": "Erro",
                "payout": "Erro",
                "balance": "Erro",
                "trade_value": "Erro",
                "duration": "Erro",
                "unknown_fields": [],
            }

        return {
            "status": "READY",
            "message": "Ultima leitura carregada do live-once.",
            "timestamp": data.get("timestamp", "UNKNOWN"),
            "window_title": data.get("window_title", "UNKNOWN"),
            "asset": data.get("asset") or "UNKNOWN",
            "price": data.get("price") or "UNKNOWN",
            "payout": data.get("payout") or "UNKNOWN",
            "balance": data.get("balance") or "UNKNOWN",
            "trade_value": data.get("trade_value") or "UNKNOWN",
            "duration": data.get("duration") or "UNKNOWN",
            "unknown_fields": data.get("unknown_fields", []),
        }


def run_dashboard_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    open_browser: bool = True,
) -> None:
    """Run the local dashboard server."""
    server = ThreadingHTTPServer((host, port), DashboardRequestHandler)
    url = f"http://{host}:{port}/"

    print("PredixAI Dashboard iniciado.")
    print(f"Acesse: {url}")
    print("Pressione Ctrl+C para encerrar.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dashboard encerrado.")
    finally:
        server.server_close()
