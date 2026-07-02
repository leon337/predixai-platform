const LAST_READING_URL = "/api/last-reading";
const PRICE_HISTORY_URL = "/api/price-history";

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const element = byId(id);
  if (!element) return;
  element.textContent = value === null || value === undefined || value === "" ? "--" : String(value);
}

function formatNumber(value, digits = 5) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits).replace(/\.?0+$/, "");
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const prefix = Number(value) > 0 ? "+" : "";
  return `${prefix}${Number(value).toFixed(3)}%`;
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function formatDateTime(value) {
  const date = parseDate(value);
  if (!date) return "--";
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function directionLabel(value) {
  if (value === "UP") return "Subiu";
  if (value === "DOWN") return "Caiu";
  if (value === "LATERAL") return "Lateral";
  return "--";
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function updateLastReading() {
  try {
    const payload = await fetchJson(LAST_READING_URL);

    setText("reading_status", payload.status || "NO_DATA");
    setText("reading_timestamp", formatDateTime(payload.timestamp));

    setText("asset", payload.asset);
    setText("price", payload.price);
    setText("payout", payload.payout);
    setText("balance", payload.balance);
    setText("trade_value", payload.trade_value);
    setText("duration", payload.duration);
  } catch (error) {
    setText("reading_status", "Erro ao ler runtime");
  }
}

async function updateHistory() {
  try {
    const payload = await fetchJson(PRICE_HISTORY_URL);
    const points = Array.isArray(payload.points) ? payload.points : [];
    const stats = payload.stats || {};

    setText("history_status", `${stats.total_points || 0} leituras`);
    setText("session_start", formatDateTime(stats.start_timestamp));
    setText("session_end", formatDateTime(stats.end_timestamp));
    setText("first_price", formatNumber(stats.first));
    setText("last_price", formatNumber(stats.last));
    setText("period_variation", `${formatNumber(stats.variation)} (${formatPercent(stats.variation_percent)})`);
    setText("period_direction", directionLabel(stats.direction));

    setText("minimum", formatNumber(stats.minimum));
    setText("maximum", formatNumber(stats.maximum));
    setText("average", formatNumber(stats.average));
    setText("amplitude", formatNumber(stats.amplitude));
    setText("history_count", stats.count || 0);
    setText("history_limit", stats.history_limit || "--");

    drawChart(points);
  } catch (error) {
    setText("history_status", "Erro no historico");
  }
}

function getValidPoints(points) {
  return points
    .map((point, index) => ({
      index,
      timestamp: point.timestamp,
      label: formatDateTime(point.timestamp),
      price: Number(point.price_value),
    }))
    .filter((point) => !Number.isNaN(point.price));
}

function drawChart(points) {
  const canvas = byId("price_chart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  const valid = getValidPoints(points);
  const padding = { left: 72, right: 28, top: 24, bottom: 58 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  ctx.font = "14px Arial";
  ctx.fillStyle = "#94a3b8";

  if (valid.length < 2) {
    ctx.fillText("Aguardando historico suficiente para desenhar o grafico.", padding.left, height / 2);
    return;
  }

  const prices = valid.map((point) => point.price);
  let min = Math.min(...prices);
  let max = Math.max(...prices);

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const yFor = (price) => {
    const ratio = (price - min) / (max - min);
    return padding.top + chartHeight - ratio * chartHeight;
  };

  const xFor = (index) => {
    if (valid.length === 1) return padding.left;
    return padding.left + (index / (valid.length - 1)) * chartWidth;
  };

  // Grid horizontal
  ctx.strokeStyle = "rgba(148, 163, 184, 0.22)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    const labelValue = max - ((max - min) / 4) * i;
    ctx.fillStyle = "#94a3b8";
    ctx.fillText(formatNumber(labelValue), 12, y + 4);
  }

  // Linha do preco
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 2;
  ctx.beginPath();

  valid.forEach((point, index) => {
    const x = xFor(index);
    const y = yFor(point.price);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();

  // Pontos inicial e final
  const first = valid[0];
  const last = valid[valid.length - 1];

  ctx.fillStyle = "#e5e7eb";
  [first, last].forEach((point) => {
    const x = xFor(point.index);
    const y = yFor(point.price);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });

  // Labels de horario no eixo X
  const tickCount = Math.min(6, valid.length);
  ctx.fillStyle = "#94a3b8";
  ctx.font = "13px Arial";

  for (let i = 0; i < tickCount; i += 1) {
    const rawIndex = Math.round((valid.length - 1) * (i / (tickCount - 1)));
    const point = valid[rawIndex];
    const x = xFor(rawIndex);
    const y = height - 24;

    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, height - padding.bottom + 8);
    ctx.strokeStyle = "rgba(148, 163, 184, 0.10)";
    ctx.stroke();

    ctx.fillStyle = "#94a3b8";
    ctx.fillText(point.label, Math.max(8, Math.min(x - 28, width - 90)), y);
  }

  // Resumo no topo do grafico
  ctx.fillStyle = "#cbd5e1";
  ctx.font = "14px Arial";
  ctx.fillText(`Leituras: ${valid.length}`, padding.left, 18);
}

async function refreshDashboard() {
  await updateLastReading();
  await updateHistory();
}

refreshDashboard();
setInterval(refreshDashboard, 5000);
