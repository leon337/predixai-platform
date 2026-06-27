"""Local dashboard server for PredixAI BR."""

from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Serve the initial PredixAI dashboard shell."""

    root = Path(__file__).parent

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send_file(self.root / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if self.path == "/static/style.css":
            self._send_file(self.root / "static" / "style.css", "text/css; charset=utf-8")
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
