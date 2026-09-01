const STORAGE_KEY = "conectatel.concierge.conversations.v1";
const form = document.querySelector("#question-form");
const question = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const chat = document.querySelector("#chat");
const metrics = document.querySelector("#metrics");
const conversationList = document.querySelector("#conversation-list");
const apiUrl = window.CONCIERGE_CONFIG?.apiUrl;

let conversations = loadConversations();
let activeConversationId = conversations[0]?.id || "";
if (!activeConversationId) createConversation();

function newId() { return window.crypto?.randomUUID?.() || `chat_${Date.now()}_${Math.random().toString(16).slice(2)}`; }
function loadConversations() { try { const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); return Array.isArray(value) ? value : []; } catch (_error) { return []; } }
function saveConversations() { localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations)); }
function createConversation() { const item = { id: newId(), title: "Nova conversa", messages: [] }; conversations.unshift(item); activeConversationId = item.id; saveConversations(); return item.id; }
function activeConversation() { return conversations.find((item) => item.id === activeConversationId); }
function escapeHtml(value) { const element = document.createElement("div"); element.textContent = String(value ?? ""); return element.innerHTML; }
function formatDuration(value) { return Number.isFinite(value) ? `${(value / 1000).toFixed(value >= 1000 ? 1 : 2)} s` : "—"; }

function renderConversations() {
  conversationList.innerHTML = conversations.map((item) => `<button class="conversation ${item.id === activeConversationId ? "active" : ""}" type="button" data-id="${item.id}"><span>${escapeHtml(item.title)}</span><small>${item.messages.length} mensagens</small></button>`).join("");
}
function responseHtml(data) {
  const citations = (data.citations || []).map((item) => `<li><strong>${escapeHtml(item.source_file)}</strong><br><code>${escapeHtml(item.chunk_id)}</code><span>score ${Number(item.score).toFixed(3)} · ${escapeHtml(item.status)}</span></li>`).join("");
  const handoffDetails = data.handoff?.protocolo_atendimento ? `<dl class="handoff-details"><div><dt>Protocolo</dt><dd>${escapeHtml(data.handoff.protocolo_atendimento)}</dd></div><div><dt>Categoria</dt><dd>${escapeHtml(data.handoff.categoria_motivo)}</dd></div><div><dt>Produto</dt><dd>${escapeHtml(data.handoff.produto_servico_envolvido)}</dd></div><div><dt>Status</dt><dd>${escapeHtml(data.handoff.status_escalonamento)}</dd></div></dl>` : "";
  const handoff = data.handoff ? `<div class="handoff"><strong>Encaminhamento humano</strong><span>${escapeHtml(data.handoff.reason)} · prioridade ${escapeHtml(data.handoff.priority)}</span><p>${escapeHtml(data.handoff.requested_action)}</p>${handoffDetails}</div>` : "";
  const sourceBlock = citations ? `<details><summary>Fontes vigentes (${data.citations.length})</summary><ul class="citations">${citations}</ul></details>` : "";
  const guardrail = data.guardrail ? `<p class="guardrail">Guardrail: ${escapeHtml(data.guardrail)}</p>` : "";
  return `<article class="assistant-card ${escapeHtml(data.decision)}"><div class="decision-line"><span class="badge">${escapeHtml(data.decision)}</span><span>${formatDuration(data.duration_ms)}</span></div><p class="answer">${escapeHtml(data.answer)}</p>${sourceBlock}${handoff}${guardrail}<footer>Trace ID: <code>${escapeHtml(data.trace_id)}</code></footer></article>`;
}
function renderChat() {
  const conversation = activeConversation();
  if (!conversation?.messages.length) { chat.innerHTML = `<div class="empty-chat"><span>✦</span><h2>Como posso ajudar?</h2><p>As respostas usam documentos vigentes e exibem suas evidências.</p></div>`; return; }
  chat.innerHTML = conversation.messages.map((message) => {
    if (message.role === "user") return `<article class="message user-message"><span>Você</span><p>${escapeHtml(message.text)}</p></article>`;
    if (message.role === "loading") return `<article class="message assistant-message loading"><span>Concierge</span><p>Consultando RAG, evidências e regras de segurança…</p></article>`;
    return `<article class="message assistant-message"><span>Concierge</span>${responseHtml(message.data)}</article>`;
  }).join(""); chat.scrollTop = chat.scrollHeight;
}
function renderMetrics() {
  const replies = conversations.flatMap((item) => item.messages).filter((item) => item.role === "assistant").map((item) => item.data);
  const count = (decision) => replies.filter((item) => item.decision === decision).length;
  const average = replies.length ? replies.reduce((total, item) => total + Number(item.duration_ms || 0), 0) / replies.length : null;
  metrics.innerHTML = [["Consultas", replies.length, "na sessão"], ["ANSWER", count("ANSWER"), "com evidências"], ["NO_ANSWER", count("NO_ANSWER"), "abstenções seguras"], ["ESCALATE", count("ESCALATE"), "handoffs"], ["Latência média", formatDuration(average), "respostas"]].map(([label, value, note]) => `<div class="metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join("");
}
function render() { renderConversations(); renderChat(); renderMetrics(); }
function addMessage(message) { const item = activeConversation(); item.messages.push(message); if (message.role === "user" && item.title === "Nova conversa") item.title = message.text.slice(0, 38); saveConversations(); }
async function submitQuestion(value) {
  if (!apiUrl) throw new Error("Configure a URL da API em config.js antes de publicar.");
  addMessage({ role: "user", text: value }); addMessage({ role: "loading" }); render();
  try {
    const response = await fetch(apiUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: value }) });
    const data = await response.json(); const item = activeConversation(); item.messages = item.messages.filter((message) => message.role !== "loading");
    if (!response.ok) throw new Error(data.message || "Não foi possível concluir a consulta.");
    addMessage({ role: "assistant", data });
  } catch (error) {
    const item = activeConversation(); item.messages = item.messages.filter((message) => message.role !== "loading");
    addMessage({ role: "assistant", data: { decision: "ERROR", answer: error.message || "Falha de conexão com a demonstração.", citations: [], duration_ms: null, trace_id: "não disponível" } });
  }
  saveConversations(); render();
}
form.addEventListener("submit", async (event) => { event.preventDefault(); const value = question.value.trim(); if (!value) return; submitButton.disabled = true; question.value = ""; await submitQuestion(value); submitButton.disabled = false; question.focus(); });
question.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
document.querySelector("#new-chat").addEventListener("click", () => { createConversation(); render(); question.focus(); });
document.querySelector("#clear-history").addEventListener("click", () => { if (window.confirm("Excluir todas as conversas salvas neste navegador?")) { conversations = []; createConversation(); render(); } });
conversationList.addEventListener("click", (event) => { const button = event.target.closest("[data-id]"); if (button) { activeConversationId = button.dataset.id; render(); } });
document.querySelectorAll("[data-question]").forEach((button) => button.addEventListener("click", () => { question.value = button.dataset.question; question.focus(); }));
render();
