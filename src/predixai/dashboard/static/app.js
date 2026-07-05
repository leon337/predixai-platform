const LAST_READING_URL = "/api/last-reading";
const PRICE_HISTORY_URL = "/api/price-history";

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const element = byId(id);
  if (!element) return;
  element.textContent = value === null || value === undefined || value === "" || value === "UNKNOWN" ? "--" : String(value);
}

function parseNumber(value) {
  if (value === null || value === undefined || value === "" || value === "UNKNOWN") return null;
  let text = String(value).replace("R$", "").replace("D", "").replace("%", "").trim();
  text = text.replace(/\s/g, "");
  if (text.includes(",") && text.includes(".")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else {
    text = text.replace(",", ".");
  }
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatPrice(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  });
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function formatTime(value) {
  const date = parseDate(value);
  if (!date) return "--";
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function ageText(value) {
  const date = parseDate(value);
  if (!date) return "--";
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s atrás`;
  return `${Math.round(seconds / 60)}min atrás`;
}

function fetchJson(url, options = {}) {
  return fetch(url, { cache: "no-store", ...options }).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
}

function extractPrices(points) {
  if (!Array.isArray(points)) return [];
  return points
    .map((point) => parseNumber(point.price_value ?? point.price))
    .filter((price) => price !== null && price > 0);
}

function analyze(prices) {
  const series = prices.slice(-80);

  if (series.length < 5) {
    return {
      signal: "AGUARDAR",
      state: "COLETANDO DADOS",
      confidence: 20,
      direction: "AGUARDANDO",
      support: null,
      resistance: null,
      average: null,
      amplitude: null,
      volatility: null,
      zone: "SEM DADOS",
      trigger: null,
      expiration: "Aguardar",
      reason: "Histórico pequeno. Aguardando mais leituras válidas.",
      block: "Não simular entrada ainda.",
      quality: "BAIXA",
    };
  }

  const windowPrices = series.slice(-20);
  const current = series[series.length - 1];
  const support = Math.min(...windowPrices);
  const resistance = Math.max(...windowPrices);
  const amplitude = resistance - support;
  const average = windowPrices.reduce((a, b) => a + b, 0) / windowPrices.length;
  const volatility = average ? (amplitude / average) * 100 : 0;

  const early = series.length >= 8
    ? series.slice(-8, -4).reduce((a, b) => a + b, 0) / 4
    : series.slice(0, 2).reduce((a, b) => a + b, 0) / 2;

  const late = series.slice(-4).reduce((a, b) => a + b, 0) / Math.min(4, series.length);
  const delta = late - early;
  const threshold = Math.max(amplitude * 0.12, current * 0.00008);

  let direction = "LATERAL";
  if (delta > threshold) direction = "SUBINDO";
  if (delta < -threshold) direction = "CAINDO";

  const position = amplitude <= 0 ? 0.5 : (current - support) / amplitude;
  const nearSupport = position <= 0.22;
  const nearResistance = position >= 0.78;

  let signal = "AGUARDAR";
  let confidence = 35;
  let trigger = null;
  let expiration = "Aguardar suporte/resistência";
  let state = "AGUARDAR CONFIRMAÇÃO";
  let reason = "Preço fora de zona clara.";
  let block = "Aguardar preço chegar em suporte ou resistência.";
  let zone = "NEUTRA";

  if (nearSupport) zone = "PERTO DO SUPORTE";
  if (nearResistance) zone = "PERTO DA RESISTÊNCIA";

  if (nearSupport && ["SUBINDO", "LATERAL"].includes(direction)) {
    signal = "COMPRA";
    confidence = direction === "SUBINDO" ? 72 : 58;
    trigger = support + amplitude * 0.15;
    expiration = "1 MIN";
    state = confidence >= 70 ? "PRONTO PARA SIMULAR" : "SINAL MÉDIO";
    reason = "Preço próximo do suporte com possível reação compradora.";
    block = `Não entrar se romper abaixo de ${formatPrice(support)}.`;
  } else if (nearResistance && ["CAINDO", "LATERAL"].includes(direction)) {
    signal = "VENDA";
    confidence = direction === "CAINDO" ? 72 : 58;
    trigger = resistance - amplitude * 0.15;
    expiration = "1 MIN";
    state = confidence >= 70 ? "PRONTO PARA SIMULAR" : "SINAL MÉDIO";
    reason = "Preço próximo da resistência com possível rejeição.";
    block = `Não entrar se romper acima de ${formatPrice(resistance)}.`;
  } else if (volatility < 0.02) {
    confidence = 25;
    reason = "Amplitude pequena. Mercado travado/lateral.";
    block = "Evitar simulação em lateralidade estreita.";
  }

  const quality = series.length >= 20 && confidence >= 65 ? "ALTA" : series.length >= 10 ? "MÉDIA" : "BAIXA";

  return {
    signal,
    state,
    confidence,
    direction,
    support,
    resistance,
    average,
    amplitude,
    volatility,
    zone,
    trigger,
    expiration,
    reason,
    block,
    quality,
  };
}

function detectResult(text) {
  const source = String(text || "");
  if (/\+\s*(D|R\$)?\s*\d/i.test(source)) return "WIN ESTIMADO";
  if (/-\s*(D|R\$)?\s*\d/i.test(source)) return "LOSS ESTIMADO";
  return "DESCONHECIDO";
}

function drawMiniChart(prices, smart) {
  const canvas = byId("mini_chart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = { left: 28, right: 18, top: 18, bottom: 28 };

  ctx.clearRect(0, 0, width, height);

  const series = prices.slice(-60);

  if (series.length < 2) {
    ctx.fillStyle = "#8e97a4";
    ctx.font = "14px Consolas";
    ctx.fillText("Aguardando histórico...", 24, height / 2);
    return;
  }

  let min = Math.min(...series);
  let max = Math.max(...series);

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const xFor = (index) => padding.left + (index / Math.max(1, series.length - 1)) * chartWidth;
  const yFor = (price) => padding.top + chartHeight - ((price - min) / (max - min)) * chartHeight;

  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  if (smart.support !== null) {
    ctx.strokeStyle = "rgba(52,255,141,0.65)";
    ctx.setLineDash([5, 4]);
    const y = yFor(smart.support);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  if (smart.resistance !== null) {
    ctx.strokeStyle = "rgba(255,79,99,0.65)";
    ctx.setLineDash([5, 4]);
    const y = yFor(smart.resistance);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  const gradient = ctx.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, "rgba(0,242,255,0.05)");
  gradient.addColorStop(1, "rgba(0,242,255,1)");

  ctx.strokeStyle = gradient;
  ctx.lineWidth = 4;
  ctx.beginPath();
  series.forEach((price, index) => {
    const x = xFor(index);
    const y = yFor(price);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const last = series[series.length - 1];
  ctx.fillStyle = "#00f2ff";
  ctx.beginPath();
  ctx.arc(xFor(series.length - 1), yFor(last), 5, 0, Math.PI * 2);
  ctx.fill();
}

function updateSignalVisual(signal) {
  const box = byId("signal_box");
  if (!box) return;

  box.classList.remove("buy", "sell");

  if (signal === "COMPRA") box.classList.add("buy");
  if (signal === "VENDA") box.classList.add("sell");
}

function updateRobotLog(smart, points) {
  const log = byId("robot_log");
  if (!log) return;

  const now = new Date().toLocaleTimeString("pt-BR");
  log.innerHTML = `
    <p>${now} [SYSTEM] Leituras válidas: ${points.length}</p>
    <p>${now} [ANALYSIS] Direção: ${smart.direction}</p>
    <p>${now} [ZONE] ${smart.zone}</p>
    <p>${now} [SIGNAL] ${smart.signal} · confiança ${smart.confidence}%</p>
  `;
}

async function updateDashboard() {
  let last = {};
  let historyPayload = { points: [], stats: {} };

  try {
    last = await fetchJson(LAST_READING_URL);
  } catch {
    last = { status: "NO_DATA" };
  }

  try {
    historyPayload = await fetchJson(PRICE_HISTORY_URL);
  } catch {
    historyPayload = { points: [], stats: {} };
  }

  const points = Array.isArray(historyPayload.points) ? historyPayload.points : [];
  const stats = historyPayload.stats || {};
  const prices = extractPrices(points);
  const smart = analyze(prices);

  const asset = last.asset || stats.asset || "--";
  const result = detectResult(last.source_ocr_text);

  setText("reading_status", last.status || "NO_DATA");
  setText("asset", asset);
  setText("market_label", `OBSERVANDO MERCADO: ${asset}`);
  setText("price", formatPrice(parseNumber(last.price ?? stats.last)));
  setText("payout", last.payout);
  setText("balance", last.balance);
  setText("trade_value", last.trade_value);
  setText("duration", last.duration);
  setText("remaining_time", last.remaining_time || last.time);
  setText("last_seen", ageText(last.timestamp));
  setText("history_count", stats.count || prices.length || 0);

  setText("direction_label", smart.direction);
  setText("confidence", `${smart.confidence}%`);
  setText("support_label", `SUPORTE: ${formatPrice(smart.support)}`);
  setText("resistance_label", `RESISTÊNCIA: ${formatPrice(smart.resistance)}`);
  setText("support_strength", smart.support ? "FORTE" : "--");
  setText("resistance_strength", smart.resistance ? "MÉDIA" : "--");
  setText("average", formatPrice(smart.average));
  setText("amplitude", formatPrice(smart.amplitude));
  setText("volatility", smart.volatility === null ? "--" : `${formatNumber(smart.volatility, 3)}%`);
  setText("quality", smart.quality);
  setText("zone", smart.zone);

  setText("signal", smart.signal);
  setText("state", smart.state);
  setText("entry_price", formatPrice(smart.trigger));
  setText("expiration", smart.expiration);
  setText("reason", smart.reason);
  setText("block_reason", smart.block);

  setText("last_entry", `${asset} ${smart.signal}`);
  setText("last_result", result);
  setText("win_rate", result === "WIN ESTIMADO" ? "Atualizando" : "--");
  setText("adjustment", smart.confidence < 50 ? "Aguardar nova zona clara." : "Manter observação no gatilho.");

  updateSignalVisual(smart.signal);
  updateRobotLog(smart, prices);
  drawMiniChart(prices, smart);
}

async function startReader(interval) {
  await fetchJson("/api/control/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interval }),
  });
  await updateDashboard();
}

async function stopReader() {
  await fetchJson("/api/control/stop", { method: "POST" });
  await updateDashboard();
}

async function clearData() {
  await fetchJson("/api/runtime/clear", { method: "POST" });
  await updateDashboard();
}

function bindControls() {
  byId("open_broker")?.addEventListener("click", () => {
    const log = byId("robot_log");
    if (log) {
      const now = new Date().toLocaleTimeString("pt-BR");
      log.insertAdjacentHTML("afterbegin", `<p>${now} [SAFE] Corretora real bloqueada neste modo simulado.</p>`);
    }
    window.alert("Corretora real bloqueada: este modo nao abre corretora, nao faz login e nao envia ordem.");
  });
  byId("start_3")?.addEventListener("click", () => startReader(3));
  byId("start_5")?.addEventListener("click", () => startReader(5));
  byId("stop_reader")?.addEventListener("click", stopReader);
  byId("clear_data")?.addEventListener("click", clearData);
}

bindControls();
updateDashboard();
setInterval(updateDashboard, 1500);
