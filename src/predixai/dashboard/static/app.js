function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "UNKNOWN") {
    return "UNKNOWN";
  }

  const number = Number(value);
  if (Number.isNaN(number)) {
    return String(value);
  }

  return number.toFixed(2);
}

async function loadLastReading() {
  const fields = ["asset", "price", "payout", "balance", "trade_value", "duration"];

  try {
    const response = await fetch("/api/last-reading", { cache: "no-store" });
    const data = await response.json();

    fields.forEach((field) => {
      setText(field, data[field] || "UNKNOWN");
    });

    setText("reading_status", data.message || "Status indisponivel.");
    setText("reading_timestamp", data.timestamp ? `Ultima leitura: ${data.timestamp}` : "");

    const values = data.unknown_fields || [];
    setText("reading_unknown_fields", values.length ? `Campos UNKNOWN: ${values.join(", ")}` : "Campos UNKNOWN: 0");
  } catch (error) {
    setText("reading_status", `Erro ao carregar leitura: ${error}`);
  }
}

async function loadPriceHistory() {
  try {
    const response = await fetch("/api/price-history", { cache: "no-store" });
    const data = await response.json();
    const points = data.points || [];
    const stats = data.stats || {};

    setText("history_status", data.message || "Historico indisponivel.");
    setText("history_count", `${stats.count || 0} leituras`);
    setText("stat_minimum", formatPrice(stats.minimum));
    setText("stat_maximum", formatPrice(stats.maximum));
    setText("stat_average", formatPrice(stats.average));
    setText("stat_amplitude", formatPrice(stats.amplitude));

    drawPriceChart(points);
  } catch (error) {
    setText("history_status", `Erro ao carregar historico: ${error}`);
    drawPriceChart([]);
  }
}

function drawPriceChart(points) {
  const canvas = document.getElementById("price_chart");
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = 48;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 4; i += 1) {
    const y = padding + ((height - padding * 2) / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  const validPoints = points.filter((point) => typeof point.price_value === "number");

  if (validPoints.length === 0) {
    ctx.fillStyle = "#94a3b8";
    ctx.font = "20px Arial";
    ctx.fillText("Sem historico suficiente para desenhar o grafico.", padding, height / 2);
    return;
  }

  const prices = validPoints.map((point) => point.price_value);
  let min = Math.min(...prices);
  let max = Math.max(...prices);

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const xForIndex = (index) => {
    if (validPoints.length === 1) {
      return padding + chartWidth / 2;
    }

    return padding + (chartWidth / (validPoints.length - 1)) * index;
  };

  const yForPrice = (price) => {
    return padding + chartHeight - ((price - min) / (max - min)) * chartHeight;
  };

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();

  validPoints.forEach((point, index) => {
    const x = xForIndex(index);
    const y = yForPrice(point.price_value);

    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.stroke();

  validPoints.forEach((point, index) => {
    const x = xForIndex(index);
    const y = yForPrice(point.price_value);

    ctx.fillStyle = "#e5e7eb";
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = "#94a3b8";
  ctx.font = "14px Arial";
  ctx.fillText(`Max: ${max.toFixed(2)}`, padding, 24);
  ctx.fillText(`Min: ${min.toFixed(2)}`, padding, height - 18);
}

function refreshDashboard() {
  loadLastReading();
  loadPriceHistory();
}

refreshDashboard();
setInterval(refreshDashboard, 5000);
