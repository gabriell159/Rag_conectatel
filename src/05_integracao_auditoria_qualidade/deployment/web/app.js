const form = document.querySelector("#question-form");
const question = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const result = document.querySelector("#result");
const apiUrl = window.CONCIERGE_CONFIG?.apiUrl;

function showResult(content, status = "") {
  result.className = `result ${status}`;
  result.innerHTML = content;
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = String(value ?? "");
  return element.innerHTML;
}

function renderResponse(data) {
  const citations = (data.citations || []).map((citation) =>
    `<li><strong>${escapeHtml(citation.source_file)}</strong> — ${escapeHtml(citation.chunk_id)} (score ${Number(citation.score).toFixed(3)})</li>`
  ).join("");
  const handoff = data.handoff
    ? `<h3>Encaminhamento</h3><p><strong>Motivo:</strong> ${escapeHtml(data.handoff.reason)}<br><strong>Ação:</strong> ${escapeHtml(data.handoff.requested_action)}<br><strong>Prioridade:</strong> ${escapeHtml(data.handoff.priority)}</p>`
    : "";
  showResult(`
    <span class="badge ${escapeHtml(data.decision)}">${escapeHtml(data.decision)}</span>
    <h2>Resposta</h2>
    <p>${escapeHtml(data.answer)}</p>
    ${citations ? `<h3>Fontes vigentes</h3><ul>${citations}</ul>` : ""}
    ${handoff}
    <p class="trace">Trace ID: ${escapeHtml(data.trace_id)}</p>
  `, data.decision);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!apiUrl) {
    showResult("Configure a URL da API em <code>config.js</code> antes de publicar.", "error");
    return;
  }
  submitButton.disabled = true;
  submitButton.textContent = "Consultando...";
  showResult("Buscando informações no corpus oficial...", "loading");
  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.value.trim() }),
    });
    const data = await response.json();
    if (!response.ok) {
      showResult(escapeHtml(data.message || "Não foi possível concluir a consulta."), response.status === 503 ? "offline" : "error");
      return;
    }
    renderResponse(data);
  } catch (_error) {
    showResult("Falha de conexão com a demonstração.", "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Consultar";
  }
});
