#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/leo/Documentos/GitHub/predixai-platform"
REPORT_DIR="/home/leo/Documentos/PredixAI_Auditorias"
REPORT="$REPORT_DIR/PREDIXAI_STARTUP_REPORT.txt"
START_PAGE="$REPORT_DIR/PREDIXAI_STARTUP_PAGE.html"

MOBILE_PORT="8766"
DASHBOARD_PORT="8765"

mkdir -p "$REPORT_DIR"
cd "$ROOT"

open_file() {
  local file="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$file" >/dev/null 2>&1 || true
  elif command -v xed >/dev/null 2>&1; then
    xed "$file" >/dev/null 2>&1 || true
  elif command -v code >/dev/null 2>&1; then
    code "$file" >/dev/null 2>&1 || true
  fi
}

{
echo "========================================"
echo "PREDIXAI BR — STARTUP MOBILE-FIRST"
echo "Data: $(date)"
echo "Repo: $ROOT"
echo "========================================"
echo

if [ ! -x ".venv/bin/python" ]; then
  echo "BLOCKER: .venv/bin/python não encontrado."
  exit 1
fi

echo "Python:"
.venv/bin/python --version
echo

echo "Encerrando portas antigas..."
fuser -k ${MOBILE_PORT}/tcp 2>/dev/null || true
fuser -k ${DASHBOARD_PORT}/tcp 2>/dev/null || true
sleep 1

echo "Iniciando Mobile Server..."
PYTHONPATH="$ROOT/src" .venv/bin/python scripts/predixai_trader_mobile_server.py --host 0.0.0.0 --port "$MOBILE_PORT" > /tmp/predixai_mobile.log 2>&1 &
MOBILE_PID=$!

echo "Iniciando Dashboard..."
PYTHONPATH="$ROOT/src" .venv/bin/python -c "from predixai.dashboard.dashboard_server import run_dashboard; run_dashboard(host='127.0.0.1', port=$DASHBOARD_PORT, open_browser=False)" > /tmp/predixai_dashboard.log 2>&1 &
DASHBOARD_PID=$!

sleep 4

echo
echo "Status:"
curl -fsS "http://127.0.0.1:$MOBILE_PORT/mobile" >/dev/null && echo "Mobile ..... OK" || echo "Mobile ..... FALHOU"
curl -fsS "http://127.0.0.1:$MOBILE_PORT/api/mobile/state" >/dev/null && echo "API Mobile ..... OK" || echo "API Mobile ..... FALHOU"
curl -fsS "http://127.0.0.1:$DASHBOARD_PORT/" >/dev/null && echo "Dashboard ..... OK" || echo "Dashboard ..... FALHOU"

echo
echo "Links:"
echo "Dashboard: http://127.0.0.1:$DASHBOARD_PORT/"
echo "Mobile:    http://127.0.0.1:$MOBILE_PORT/mobile"
echo "API:       http://127.0.0.1:$MOBILE_PORT/api/mobile/state"
echo
echo "Mobile PID: $MOBILE_PID"
echo "Dashboard PID: $DASHBOARD_PID"
echo
echo "PASS: Ambiente iniciado."
} | tee "$REPORT"

cat > "$START_PAGE" <<HTML
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>PredixAI Startup</title>
<style>
body{background:#061018;color:#eaf7ff;font-family:Arial;padding:40px}
.card{border:1px solid #00e5ff;border-radius:16px;padding:24px;margin:16px 0;background:#0b1622}
a{color:#00e5ff;font-size:22px;font-weight:bold}
.status{color:#38d66b;font-size:28px}
</style>
</head>
<body>
<h1>PredixAI BR — Ambiente Mobile-First</h1>
<div class="card"><div class="status">AMBIENTE INICIADO</div></div>
<div class="card"><a href="http://127.0.0.1:$DASHBOARD_PORT/">Abrir Dashboard</a></div>
<div class="card"><a href="http://127.0.0.1:$MOBILE_PORT/mobile">Abrir Aplicativo Mobile</a></div>
<div class="card"><a href="http://127.0.0.1:$MOBILE_PORT/api/mobile/state">Ver API Mobile</a></div>
<p>Modo: 100% simulado. Sem ordem real, sem login, sem saldo real.</p>
</body>
</html>
HTML

echo "Relatório: $REPORT"
echo "Página inicial: $START_PAGE"

open_file "$REPORT"
open_file "$START_PAGE"
