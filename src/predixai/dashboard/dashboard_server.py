"""Local dashboard server for PredixAI BR."""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Serve the PredixAI dashboard and runtime live reading data."""

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

        if self.path == "/api/price-history":
            self._send_json(self._load_price_history())
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

    def _send_json(self, data: object) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _load_last_reading(self) -> dict[str, object]:
        reading_path = self.project_root / "data" / "runtime" / "last_live_reading.json"

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

    def _load_price_history(self) -> dict[str, object]:
        history_path = self.project_root / "data" / "runtime" / "live_price_history.json"

        if not history_path.exists():
            return {
                "status": "WAITING",
                "message": "Historico de precos ainda nao encontrado.",
                "points": [],
                "stats": {
                    "count": 0,
                    "minimum": "UNKNOWN",
                    "maximum": "UNKNOWN",
                    "average": "UNKNOWN",
                    "amplitude": "UNKNOWN",
                },
            }

        try:
            points = json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "status": "ERROR",
                "message": f"Falha ao ler historico: {exc}",
                "points": [],
                "stats": {
                    "count": 0,
                    "minimum": "UNKNOWN",
                    "maximum": "UNKNOWN",
                    "average": "UNKNOWN",
                    "amplitude": "UNKNOWN",
                },
            }

        if not isinstance(points, list):
            points = []

        clean_points = []
        prices = []

        for index, point in enumerate(points[-50:], start=1):
            if not isinstance(point, dict):
                continue

            price_value = point.get("price_value")
            if isinstance(price_value, (int, float)):
                prices.append(float(price_value))

            clean_points.append(
                {
                    "index": index,
                    "timestamp": point.get("timestamp", "UNKNOWN"),
                    "asset": point.get("asset", "UNKNOWN"),
                    "price": point.get("price", "UNKNOWN"),
                    "price_value": price_value,
                    "confidence": point.get("confidence", 0.0),
                }
            )

        if prices:
            minimum = min(prices)
            maximum = max(prices)
            average = sum(prices) / len(prices)
            amplitude = maximum - minimum
            stats = {
                "count": len(prices),
                "minimum": round(minimum, 5),
                "maximum": round(maximum, 5),
                "average": round(average, 5),
                "amplitude": round(amplitude, 5),
            }
        else:
            stats = {
                "count": 0,
                "minimum": "UNKNOWN",
                "maximum": "UNKNOWN",
                "average": "UNKNOWN",
                "amplitude": "UNKNOWN",
            }

        return {
            "status": "READY",
            "message": "Historico carregado.",
            "points": clean_points,
            "stats": stats,
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
