from __future__ import annotations

from html import escape


def render_mobile_session_start_page() -> str:
    """Renderiza a tela inicial mobile da sessão simulada.

    PTP-112B:
    - Não solicita fonte visual.
    - Não solicita acesso externo.
    - Não solicita credencial.
    - Não habilita ordem real.
    - Apenas prepara configuração simulada compatível com MobileSessionContract v1.1.
    """

    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>PredixAI Trader — Sessão Simulada</title>
  <style>
    body{margin:0;font-family:Arial,sans-serif;background:#07111f;color:#eaf4ff}
    .wrap{max-width:520px;margin:0 auto;padding:18px}
    .card{background:#0d1b2f;border:1px solid #16385f;border-radius:16px;padding:16px;margin:12px 0}
    h1{font-size:24px;margin:0 0 6px}
    h2{font-size:17px;margin:0 0 12px;color:#7dd3fc}
    label{display:block;margin-top:10px;font-size:13px;color:#b7d7ef}
    input,select{width:100%;box-sizing:border-box;margin-top:4px;padding:11px;border-radius:10px;border:1px solid #2b5680;background:#07111f;color:#eaf4ff}
    .badge{display:inline-block;margin:4px 4px 4px 0;padding:6px 9px;border-radius:999px;background:#12395d;color:#c9ecff;font-size:12px}
    .warn{font-size:13px;color:#facc15;line-height:1.35}
    button{width:100%;padding:14px;border:0;border-radius:14px;margin-top:12px;font-weight:700}
    .primary{background:#22c55e;color:#04130a}
    .secondary{background:#1e293b;color:#eaf4ff}
    pre{white-space:pre-wrap;background:#020617;border-radius:12px;padding:12px;font-size:12px}
  </style>
</head>
<body>
<div class="wrap">
  <h1>PredixAI Trader</h1>
  <div>Sessão Simulada Mobile</div>

  <div class="card">
    <span class="badge">Modo: SIMULADO</span>
    <span class="badge">Ordens reais: BLOQUEADAS</span>
    <span class="badge">Saldo: SIMULADO</span>
  </div>

  <form id="sessionForm">
    <div class="card">
      <h2>1. Sessão</h2>
      <label>Tipo de sessão</label>
      <select name="session_type">
        <option value="SCALPER">Scalper</option>
        <option value="DAY_TRADE">Day Trade</option>
      </select>

      <label>Nome da sessão</label>
      <input name="session_name" placeholder="Ex: Teste Cafeina manhã"/>
    </div>

    <div class="card">
      <h2>2. Estratégia</h2>
      <label>Modo de estratégia</label>
      <select name="strategy_mode">
        <option value="CONSERVATIVE">Conservadora</option>
        <option value="MODERATE">Moderada</option>
        <option value="AGGRESSIVE">Agressiva</option>
      </select>

      <label>Estratégia principal</label>
      <select name="primary_strategy">
        <option value="LEGACY_MOMENTUM">Legacy Momentum</option>
        <option value="SUPPORT_RESISTANCE">Support/Resistance</option>
        <option value="PRICE_ACTION">Price Action</option>
        <option value="CANDLE_REVERSAL">Candle Reversal</option>
      </select>

      <label>Confiança mínima (%)</label>
      <input name="min_confidence" type="number" min="50" max="95" value="70"/>
      <p class="warn">Estratégia sozinha não libera sinal. Confluência obrigatória.</p>
    </div>

    <div class="card">
      <h2>3. Banca Simulada</h2>
      <label>Banca inicial</label>
      <input name="initial_bankroll" type="number" min="1" step="0.01" value="100.00"/>

      <label>Entrada inicial</label>
      <input name="initial_entry" type="number" min="1" step="0.01" value="5.00"/>
      <p class="warn">A banca exibida é simulada. O saldo real da fonte visual será ignorado.</p>
    </div>

    <div class="card">
      <h2>4. Risco</h2>
      <label>Perfil de risco</label>
      <select name="risk_profile">
        <option value="CONSERVATIVE">Conservador</option>
        <option value="MODERATE">Moderado</option>
        <option value="AGGRESSIVE">Agressivo</option>
      </select>

      <label>Stop Loss</label>
      <input name="stop_loss" type="number" min="1" step="0.01" value="20.00"/>

      <label>Take Profit</label>
      <input name="take_profit" type="number" min="1" step="0.01" value="30.00"/>

      <label>Máximo de sinais</label>
      <input name="max_signals" type="number" min="1" value="10"/>

      <label>Máximo de perdas</label>
      <input name="max_losses" type="number" min="1" value="3"/>
    </div>

    <div class="card">
      <h2>5. Operação</h2>
      <label>Payout mínimo (%)</label>
      <input name="payout_min" type="number" min="50" max="100" value="80"/>

      <label>Expiração</label>
      <select name="expiration_seconds">
        <option value="30">30s</option>
        <option value="60" selected>60s</option>
        <option value="120">120s</option>
        <option value="300">300s</option>
      </select>
    </div>

    <div class="card">
      <h2>6. Recuperação Simulada</h2>
      <label>Ativar recuperação</label>
      <select name="recovery_enabled">
        <option value="false">Não</option>
        <option value="true">Sim</option>
      </select>

      <label>Modo</label>
      <select name="recovery_mode">
        <option value="NONE">Nenhum</option>
        <option value="FIXED">Simples</option>
        <option value="MULTIPLIER">Multiplicador</option>
      </select>

      <label>Máximo de etapas</label>
      <input name="max_recovery_steps" type="number" min="0" value="2"/>

      <label>Multiplicador</label>
      <input name="recovery_multiplier" type="number" min="1" step="0.1" value="1.5"/>
    </div>

    <div class="card">
      <h2>Segurança</h2>
      <pre>Execução real bloqueada
Clique automático bloqueado
Acesso externo e credencial não utilizados
Depósito e saque bloqueados</pre>
    </div>

    <button class="primary" type="submit">Iniciar Sessão Simulada</button>
    <button class="secondary" type="reset">Limpar Configuração</button>
  </form>

  <div class="card">
    <h2>Payload gerado</h2>
    <pre id="payloadPreview">Aguardando configuração...</pre>
  </div>
</div>

<script>
document.getElementById("sessionForm").addEventListener("submit", async function(ev){
  ev.preventDefault();
  const data = Object.fromEntries(new FormData(ev.target).entries());

  const payload = {
    session: {
      session_type: data.session_type,
      session_name: data.session_name || "Sessão Simulada Mobile"
    },
    strategy: {
      strategy_mode: data.strategy_mode,
      primary_strategy: data.primary_strategy,
      strategy_stack: [data.primary_strategy],
      confluence_required: true,
      min_confidence: Number(data.min_confidence)
    },
    bankroll: {
      simulated: true,
      initial_bankroll: Number(data.initial_bankroll),
      current_bankroll: Number(data.initial_bankroll),
      initial_entry: Number(data.initial_entry),
      current_entry: Number(data.initial_entry)
    },
    risk: {
      risk_profile: data.risk_profile,
      stop_loss: Number(data.stop_loss),
      take_profit: Number(data.take_profit),
      max_signals: Number(data.max_signals),
      max_losses: Number(data.max_losses)
    },
    operation: {
      paper_trade_enabled: true,
      payout_mode: "MANUAL",
      payout_min: Number(data.payout_min),
      expiration_seconds: Number(data.expiration_seconds),
      max_open_trades: 1
    },
    recovery: {
      recovery_enabled: data.recovery_enabled === "true",
      recovery_mode: data.recovery_enabled === "true" ? data.recovery_mode : "NONE",
      max_recovery_steps: Number(data.max_recovery_steps),
      recovery_multiplier: Number(data.recovery_multiplier),
      current_recovery_step: 0
    }
  };

  document.getElementById("payloadPreview").textContent = JSON.stringify(payload, null, 2);

  const response = await fetch("/mobile/session/start", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const result = await response.json();
  alert(result.ok ? "Sessão simulada preparada." : "Falha: " + result.error);
});
</script>
</body>
</html>"""


def render_payload_result(ok: bool, message: str) -> str:
    safe = escape(message)
    return f"<html><body><h1>{'OK' if ok else 'ERRO'}</h1><p>{safe}</p></body></html>"
