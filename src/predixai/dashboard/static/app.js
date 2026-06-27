async function loadLastReading() {
  const fields = ["asset", "price", "payout", "balance", "trade_value", "duration"];

  try {
    const response = await fetch("/api/last-reading", { cache: "no-store" });
    const data = await response.json();

    fields.forEach((field) => {
      const element = document.getElementById(field);
      if (element) {
        element.textContent = data[field] || "UNKNOWN";
      }
    });

    const status = document.getElementById("reading_status");
    if (status) {
      status.textContent = data.message || "Status indisponivel.";
    }

    const timestamp = document.getElementById("reading_timestamp");
    if (timestamp) {
      timestamp.textContent = data.timestamp ? `Ultima leitura: ${data.timestamp}` : "";
    }

    const unknownFields = document.getElementById("reading_unknown_fields");
    if (unknownFields) {
      const values = data.unknown_fields || [];
      unknownFields.textContent = values.length ? `Campos UNKNOWN: ${values.join(", ")}` : "Campos UNKNOWN: 0";
    }
  } catch (error) {
    const status = document.getElementById("reading_status");
    if (status) {
      status.textContent = `Erro ao carregar leitura: ${error}`;
    }
  }
}

loadLastReading();
setInterval(loadLastReading, 5000);
