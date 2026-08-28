const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const state = {
  status: null,
  providers: [],
  settings: {},
  sessions: [],
  session: null,
  models: [],
  selectedDescriptor: null,
  provider: "openai",
  filter: "all",
  sort: "",
  source: null,
  streaming: false,
  streamText: "",
  events: [],
  lastPrompt: "",
  evidence: null,
  context: null,
  trajectory: null,
  telemetry: null,
  callStartedAt: null,
  firstDeltaAt: null,
  streamedCharacters: 0,
  toolCalls: 0,
  rateHistory: [],
  latencyHistory: [],
  uptimeBase: 0,
  uptimeStartedAt: Date.now(),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const value = await response.json().catch(() => ({ error: "Malformed Cortex response." }));
  if (!response.ok) throw new Error(value.error || `Cortex service ${response.status}`);
  return value;
}

function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.toggle("error", error);
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 3200);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;",
  }[character]));
}

function markdown(text) {
  const chunks = escapeHtml(text).split(/```/);
  return chunks.map((part, index) => index % 2
    ? `<pre><button class="copy-code">COPY</button><code>${part.replace(/^\w+\n/, "")}</code></pre>`
    : part
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/^### (.*)$/gm, "<h3>$1</h3>")
      .replace(/^## (.*)$/gm, "<h2>$1</h2>")
      .replace(/^# (.*)$/gm, "<h1>$1</h1>")
      .replace(/\n/g, "<br>"))
    .join("");
}

function providerLabel(id) {
  return id === "xai" ? "xAI / Grok" : id === "openrouter" ? "OpenRouter" : "OpenAI";
}

function fmtTime(value) {
  return new Date((value || Date.now() / 1000) * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function modelLabel() {
  if (!state.session?.model_id) return "Select provider / model";
  return `${providerLabel(state.session.provider)} / ${state.session.model_id}`;
}

function setCoreState(mode, label, detail) {
  document.body.dataset.coreState = mode;
  $("#coreState").textContent = label;
  $("#coreDetail").textContent = detail;
  $("#systemState").textContent = label;
  $("#coreLiveLabel").textContent = mode === "idle" ? "STANDBY" : label;
}

function updateHeader() {
  $("#activeModel").textContent = modelLabel();
  const free = state.session?.model_id === "openrouter/free" || state.session?.model_id?.endsWith(":free");
  $("#freeBadge").classList.toggle("hidden", !free);
  $("#sessionState").textContent = state.streaming ? "ACTIVE" : state.session ? "READY" : "IDLE";
  $("#stopButton").classList.toggle("hidden", !state.streaming);
  $("#sendButton").disabled = state.streaming;
  $("#providerState").textContent = state.session?.provider ? providerLabel(state.session.provider).toUpperCase() : "NOT SELECTED";
  $("#providerDetail").textContent = state.session?.model_id || "Select a reasoning engine to begin.";
  $("#providerRail").textContent = state.session?.provider ? providerLabel(state.session.provider) : "—";
  $("#modelRail").textContent = state.session?.model_id || "—";
  $("#sessionIdReadout").textContent = state.session?.session_id ? state.session.session_id.slice(-8) : "—";
  $("#threadCount").textContent = state.sessions.length;
  $("#providerHealth").textContent = state.session?.provider ? "READY" : "STANDBY";
}

function measurementLabel(value) {
  return String(value || "unavailable").replaceAll("_", " ").toUpperCase();
}

function setMetric(valueId, classId, metric, formatter = value => String(value)) {
  const available = metric && metric.value !== null && metric.value !== undefined;
  $(valueId).textContent = available ? formatter(metric.value) : "—";
  if (classId) {
    const label = measurementLabel(metric?.measurement);
    $(classId).textContent = label;
    $(classId).classList.toggle("live", available && metric.measurement !== "unavailable");
  }
}

function addHistory(list, value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return;
  list.push(number);
  if (list.length > 48) list.shift();
}

function drawSparkline(canvas, values, startColor, endColor) {
  const rect = canvas.getBoundingClientRect();
  const dpr = devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * dpr));
  canvas.height = Math.max(1, Math.round(rect.height * dpr));
  const context = canvas.getContext("2d");
  context.scale(dpr, dpr);
  context.clearRect(0, 0, rect.width, rect.height);
  context.strokeStyle = "rgba(84, 132, 169, .16)";
  context.lineWidth = 1;
  for (let row = 1; row < 4; row += 1) {
    const y = rect.height * row / 4;
    context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke();
  }
  if (!values.length) {
    context.strokeStyle = "rgba(125, 151, 177, .28)";
    context.beginPath(); context.moveTo(0, rect.height * .72); context.lineTo(rect.width, rect.height * .72); context.stroke();
    return;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, Math.abs(max) * .08, 1);
  const gradient = context.createLinearGradient(0, 0, rect.width, 0);
  gradient.addColorStop(0, startColor);
  gradient.addColorStop(1, endColor);
  context.strokeStyle = gradient;
  context.lineWidth = 2;
  context.shadowBlur = 9;
  context.shadowColor = endColor;
  context.beginPath();
  values.forEach((value, index) => {
    const x = values.length === 1 ? rect.width : index * rect.width / (values.length - 1);
    const y = rect.height - 5 - ((value - min) / span) * (rect.height - 12);
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  context.stroke();
}

function drawCharts() {
  drawSparkline($("#tokenRateChart"), state.rateHistory, "#43c8ff", "#9a7cff");
  drawSparkline($("#latencyChart"), state.latencyHistory, "#9a7cff", "#4de8ff");
  ["confidenceChart", "cpuChart", "gpuChart", "networkChart", "uncertaintyChart"].forEach(id => {
    drawSparkline($(`#${id}`), [], "#249fff", "#23e8ff");
  });
  drawSparkline($("#healthChart"), state.streaming ? [1, 1, 1, 1] : [1], "#23e8ff", "#55ddb2");
}

function resetLiveMetrics() {
  state.callStartedAt = performance.now();
  state.firstDeltaAt = null;
  state.streamedCharacters = 0;
  state.toolCalls = 0;
  $("#tokenRate").textContent = "—";
  $("#rateClass").textContent = "AWAITING USAGE";
  $("#latencyMetric").textContent = "—";
  $("#latencyClass").textContent = "MEASURING";
  $("#firstTokenMetric").textContent = "—";
  $("#toolMetric").textContent = "0";
  $("#costMetric").textContent = "—";
  $("#costClass").textContent = "UNAVAILABLE";
  $("#telemetryState").textContent = "LIVE";
  $("#healthMetric").textContent = "ACTIVE";
}

function updateLiveDelta(payload) {
  const elapsedMs = Number(payload.elapsed_ms) || (performance.now() - state.callStartedAt);
  state.streamedCharacters = Number(payload.streamed_characters) || (state.streamedCharacters + String(payload.text || "").length);
  if (!state.firstDeltaAt) {
    state.firstDeltaAt = elapsedMs;
    $("#firstTokenMetric").textContent = elapsedMs.toFixed(0);
  }
  const estimatedTokens = state.streamedCharacters / 4;
  const estimatedRate = elapsedMs > 0 ? estimatedTokens / (elapsedMs / 1000) : 0;
  $("#tokenRate").textContent = estimatedRate.toFixed(1);
  $("#rateClass").textContent = "ESTIMATED LIVE";
  $("#rateClass").classList.add("live");
  $("#latencyMetric").textContent = elapsedMs.toFixed(0);
  $("#latencyClass").textContent = "MEASURED ELAPSED";
  addHistory(state.rateHistory, estimatedRate);
  addHistory(state.latencyHistory, elapsedMs);
  drawCharts();
}

function applyTelemetry(telemetry) {
  state.telemetry = telemetry;
  const metrics = telemetry?.metrics || {};
  setMetric("#tokenRate", "#rateClass", metrics.tokens_per_second, value => Number(value).toFixed(1));
  setMetric("#latencyMetric", "#latencyClass", metrics.model_latency, value => Number(value).toFixed(0));
  setMetric("#firstTokenMetric", null, metrics.first_token_latency, value => Number(value).toFixed(0));
  setMetric("#contextLoad", "#contextClass", metrics.context_tokens, value => Number(value).toLocaleString());
  setMetric("#costMetric", "#costClass", metrics.cost, value => Number(value).toPrecision(4));
  $("#toolMetric").textContent = metrics.tool_calls?.value ?? 0;
  $("#tokenMetric").textContent = metrics.total_tokens?.value ?? "—";
  const contextTokens = Number(metrics.context_tokens?.value);
  const contextLimit = Number(state.selectedDescriptor?.context_length);
  const hasUtilization = Number.isFinite(contextTokens) && Number.isFinite(contextLimit) && contextLimit > 0;
  const utilization = hasUtilization ? Math.min(100, contextTokens / contextLimit * 100) : null;
  $("#contextPercent").textContent = utilization == null ? "—" : `${utilization.toFixed(1)}%`;
  $("#contextBar").style.width = utilization == null ? "0" : `${utilization}%`;
  $("#contextLimit").textContent = Number.isFinite(contextLimit) && contextLimit > 0 ? contextLimit.toLocaleString() : "UNKNOWN LIMIT";
  if (metrics.tokens_per_second?.value != null) addHistory(state.rateHistory, metrics.tokens_per_second.value);
  if (metrics.model_latency?.value != null) addHistory(state.latencyHistory, metrics.model_latency.value);
  drawCharts();
}

function renderProviders() {
  const root = $("#providerCards");
  root.innerHTML = state.providers.map(provider => `
    <article class="provider-card" data-provider="${provider.provider}">
      <div><h3>${escapeHtml(provider.display_name)}</h3><span class="provider-state ${provider.status === "CONNECTED" ? "connected" : provider.status === "INVALID_KEY" ? "error" : ""}">${escapeHtml(provider.status)} · ${provider.model_count || 0} models</span></div>
      <input type="password" autocomplete="off" placeholder="${provider.configured ? escapeHtml(provider.masked) : "Enter API key"}" aria-label="${escapeHtml(provider.display_name)} API key">
      <div class="provider-actions"><button data-save>SAVE</button><button data-test>TEST CONNECTION</button></div>
    </article>`).join("");
  root.querySelectorAll("[data-save]").forEach(button => button.onclick = () => saveKey(button.closest(".provider-card")));
  root.querySelectorAll("[data-test]").forEach(button => button.onclick = () => testProvider(button.closest(".provider-card")));
}

async function saveKey(card) {
  const provider = card.dataset.provider;
  const input = card.querySelector("input");
  if (!input.value.trim()) return toast("Enter an API key first.", true);
  try {
    await api(`/v1/providers/${provider}/credential`, { method: "POST", body: JSON.stringify({ api_key: input.value }) });
    input.value = "";
    await loadProviders();
    toast(`${providerLabel(provider)} key stored in the host vault.`);
  } catch (error) { toast(error.message, true); }
}

async function testProvider(card) {
  const provider = card.dataset.provider;
  const status = card.querySelector(".provider-state");
  status.textContent = "TESTING…";
  try {
    const result = await api(`/v1/providers/${provider}/validate`, { method: "POST", body: "{}" });
    status.textContent = `${result.state} · ${result.model_count || 0} models`;
    status.className = `provider-state ${result.state === "CONNECTED" ? "connected" : "error"}`;
    await loadProviders();
    toast(result.state === "CONNECTED" ? `${providerLabel(provider)} connected.` : result.message || result.state, result.state !== "CONNECTED");
  } catch (error) { status.textContent = "CONNECTION FAILED"; toast(error.message, true); }
}

async function loadProviders() {
  const value = await api("/v1/providers");
  state.providers = value.providers;
  renderProviders();
}

async function loadInitial() {
  try {
    state.status = await api("/v1/status");
    state.uptimeBase = Number(state.status.uptime_seconds || 0);
    state.uptimeStartedAt = Date.now();
    state.settings = await api("/v1/settings");
    await loadProviders();
    state.sessions = (await api("/v1/sessions")).sessions;
    renderSessions();
    applyAppearance(state.settings.appearance || "standard");
    drawCharts();
    if (state.sessions.length) await openSession(state.sessions[0].session_id);
    else if (!state.providers.some(provider => provider.configured)) $("#settingsDialog").showModal();
  } catch (error) { toast(error.message, true); setCoreState("error", "OFFLINE", "Cortex service unavailable"); }
}

function renderSessions() {
  const root = $("#sessionList");
  root.innerHTML = state.sessions.map(session => `<button class="session-item ${state.session?.session_id === session.session_id ? "active" : ""}" data-session="${session.session_id}"><strong>${escapeHtml(session.title)}</strong><small>${escapeHtml(session.model_id || "No model")} · ${fmtTime(session.started_at)}</small></button>`).join("") || '<p class="muted">No conversations yet.</p>';
  root.querySelectorAll("[data-session]").forEach(button => button.onclick = () => openSession(button.dataset.session));
}

async function newConversation() {
  const provider = state.settings.selected_provider || state.provider || "";
  const model_id = state.settings.selected_model || "";
  const session = await api("/v1/sessions", { method: "POST", body: JSON.stringify({ provider, model_id }) });
  state.sessions.unshift(session);
  await openSession(session.session_id);
  if (!model_id) openModels();
}

async function openSession(id) {
  if (state.source) state.source.close();
  state.session = await api(`/v1/sessions/${id}`);
  state.streaming = state.session.active;
  state.streamText = "";
  state.lastPrompt = [...(state.session.messages || [])].reverse().find(message => message.role === "user")?.content || "";
  renderSessions();
  renderMessages();
  updateHeader();
  connectEvents();
  await refreshIntelligence();
  setCoreState(state.streaming ? "thinking" : "idle", state.streaming ? "THINKING" : "IDLE", state.streaming ? "Cortex runtime active" : (state.session.model_id ? "Continuity ready" : "Waiting for a reasoning engine"));
}

function renderMessages() {
  const root = $("#messages");
  const items = state.session?.messages || [];
  $("#emptyState").classList.toggle("hidden", items.length > 0);
  root.querySelectorAll(".message").forEach(node => node.remove());
  items.forEach(item => addMessage(item));
  root.scrollTop = root.scrollHeight;
  $("#conversationTitle").textContent = state.session?.title || "New conversation";
  $("#retryButton").disabled = !state.lastPrompt;
}

function addMessage(item, stream = false) {
  $("#emptyState").classList.add("hidden");
  const node = document.createElement("article");
  node.className = `message ${item.role}`;
  node.dataset.stream = stream ? "true" : "false";
  const provenance = item.role === "assistant" && item.provider ? `Reasoning engine: ${escapeHtml(providerLabel(item.provider))} / ${escapeHtml(item.model_id)}` : "";
  node.innerHTML = `<div class="message-head"><strong>${item.role === "user" ? "YOU" : "CORTEX"}</strong><span>${provenance}</span><time>${fmtTime(item.created_at)}</time></div><div class="message-body">${markdown(item.content || "")}${stream ? '<span class="stream-caret"></span>' : ""}</div>`;
  $("#messages").append(node);
  node.querySelectorAll(".copy-code").forEach(button => button.onclick = () => navigator.clipboard.writeText(button.nextElementSibling.textContent));
  return node;
}

function ensureStreamMessage() {
  let node = $('[data-stream="true"]');
  if (!node) node = addMessage({ role: "assistant", content: "", created_at: Date.now() / 1000, provider: state.session.provider, model_id: state.session.model_id }, true);
  return node;
}

function updateStream() {
  const node = ensureStreamMessage();
  node.querySelector(".message-body").innerHTML = `${markdown(state.streamText)}<span class="stream-caret"></span>`;
  const messages = $("#messages");
  if (messages.scrollHeight - messages.scrollTop - messages.clientHeight < 180) messages.scrollTop = messages.scrollHeight;
}

async function send(text) {
  if (!state.session) await newConversation();
  if (!state.session.model_id) return openModels();
  state.lastPrompt = text;
  state.session.messages.push({ role: "user", content: text, created_at: Date.now() / 1000 });
  addMessage(state.session.messages.at(-1));
  state.streaming = true;
  state.streamText = "";
  resetLiveMetrics();
  setCoreState("thinking", "THINKING", "Preparing governed context");
  updateHeader();
  try {
    await api(`/v1/sessions/${state.session.session_id}/messages`, { method: "POST", body: JSON.stringify({ text }) });
  } catch (error) {
    state.streaming = false;
    updateHeader();
    setCoreState("error", "ERROR", "Turn could not start");
    toast(error.message, true);
  }
}

function connectEvents() {
  if (!state.session) return;
  state.source = new EventSource(`/v1/events?session_id=${encodeURIComponent(state.session.session_id)}`);
  state.source.addEventListener("cortex", event => handleEvent(JSON.parse(event.data)));
  state.source.onerror = () => { if (state.streaming) $("#sessionState").textContent = "RECONNECTING"; };
}

function handleEvent(event) {
  state.events.push(event);
  if (state.events.length > 400) state.events.shift();
  logEvent(event);
  const type = event.event_type;
  const payload = event.payload || {};
  if (type === "session.started") setCoreState("context", "CONTEXT", "Opening Cortex continuity");
  if (type === "context.prepared") {
    setCoreState("thinking", "THINKING", "Context projection stabilized");
    if (payload.estimated_tokens != null) {
      $("#contextLoad").textContent = Number(payload.estimated_tokens).toLocaleString();
      $("#contextMetric").textContent = Number(payload.estimated_tokens).toLocaleString();
    }
  }
  if (type === "model.requested") setCoreState("thinking", "THINKING", `${providerLabel(state.session.provider)} / ${state.session.model_id}`);
  if (type === "model.delta") {
    state.streamText += payload.text || "";
    updateStream();
    updateLiveDelta(payload);
    setCoreState("streaming", "STREAMING", "Public response arriving");
  }
  if (type === "model.responded") {
    const usage = payload.token_usage || {};
    $("#tokenMetric").textContent = usage.total_tokens ?? usage.total ?? usage.output_tokens ?? usage.completion_tokens ?? "—";
    if (payload.tokens_per_second != null) {
      $("#tokenRate").textContent = Number(payload.tokens_per_second).toFixed(1);
      $("#rateClass").textContent = "MEASURED";
      addHistory(state.rateHistory, payload.tokens_per_second);
    }
    if (payload.model_latency_ms != null) {
      $("#latencyMetric").textContent = Number(payload.model_latency_ms).toFixed(0);
      $("#latencyClass").textContent = "MEASURED";
      addHistory(state.latencyHistory, payload.model_latency_ms);
    }
    drawCharts();
  }
  if (type === "tool.requested" || type === "tool.started") {
    setCoreState("tool", "TOOL ACTIVE", payload.tool_name || payload.name || "Bounded capability");
    logTool(event);
  }
  if (type === "tool.completed") {
    state.toolCalls += 1;
    $("#toolMetric").textContent = state.toolCalls;
    setCoreState("thinking", "THINKING", "Tool observation returned");
    logTool(event);
  }
  if (type === "chat.interrupt.requested" || type === "model.interrupted") setCoreState("interrupt", "INTERRUPTED", "Operator cancellation received");
  if (type === "chat.turn.completed") {
    state.streaming = false;
    state.streamText = "";
    $("#telemetryState").textContent = "TURN COMPLETE";
    $("#healthMetric").textContent = payload.status === "interrupted" ? "STOPPED" : "HEALTHY";
    setCoreState("idle", payload.status === "interrupted" ? "STOPPED" : "SEALED", payload.status === "interrupted" ? "Generation interrupted" : "Trajectory recorded by Cortex");
    reloadCurrent();
    toast(payload.status === "interrupted" ? "Generation interrupted." : "Trajectory sealed.");
  }
  if (type === "chat.turn.failed") {
    state.streaming = false;
    $("#healthMetric").textContent = "FAILED";
    $("#telemetryState").textContent = "TURN FAILED";
    setCoreState("error", "ERROR", payload.message || "Cortex turn failed");
    updateHeader();
    toast(payload.message || "Cortex turn failed.", true);
  }
  if (type === "model.failed") setCoreState("error", "MODEL ERROR", "Provider invocation failed");
  updateHeader();
}

function logEvent(event) {
  const root = $("#eventLog");
  if (root.querySelector(".muted")) root.innerHTML = "";
  const row = document.createElement("div");
  row.className = "event-row";
  row.innerHTML = `<span>${fmtTime(event.emitted_at)}</span><b>${escapeHtml(event.event_type)}</b><span>${escapeHtml(JSON.stringify(event.payload || {})).slice(0, 500)}</span>`;
  root.prepend(row);
}

function logTool(event) {
  const root = $("#toolLog");
  const node = document.createElement("div");
  node.className = "tool-unit";
  const duration = event.payload.duration_ms != null ? ` · ${event.payload.duration_ms} ms` : "";
  node.textContent = `${event.event_type} · ${event.payload.tool_name || event.payload.name || ""} · ${event.payload.status || ""}${duration}`;
  root.prepend(node);
}

async function reloadCurrent() {
  if (!state.session) return;
  state.session = await api(`/v1/sessions/${state.session.session_id}`);
  state.streaming = false;
  renderMessages();
  updateHeader();
  await refreshIntelligence();
}

async function refreshIntelligence() {
  if (!state.session) return;
  const id = state.session.session_id;
  [state.context, state.evidence, state.trajectory, state.telemetry] = await Promise.all([
    api(`/v1/sessions/${id}/context`), api(`/v1/sessions/${id}/evidence`),
    api(`/v1/sessions/${id}/trajectory`), api(`/v1/sessions/${id}/telemetry`),
  ]);
  $("#verifiedCount").textContent = state.evidence.verified;
  $("#supportedCount").textContent = state.evidence.supported;
  $("#unknownCount").textContent = state.evidence.unknown;
  $("#contradictedCount").textContent = state.evidence.contradicted;
  $("#trajectoryHash").textContent = state.evidence.receipt_hash || "No completed turn.";
  $("#memoryProjected").textContent = `${state.evidence.memory.projected} projected`;
  $("#memoryMetric").textContent = state.evidence.memory.projected;
  $("#memoryConsidered").textContent = state.evidence.memory.considered;
  $("#memoryProjectedCount").textContent = state.evidence.memory.projected;
  $("#memoryActivity").textContent = state.evidence.memory.projected ? "ACTIVE" : "INACTIVE";
  const memoryRatio = state.evidence.memory.considered ? Math.min(100, state.evidence.memory.projected / state.evidence.memory.considered * 100) : 0;
  $("#memoryBar").style.width = `${memoryRatio}%`;
  $("#memoryUtilBar").style.width = `${memoryRatio}%`;
  $("#memoryState").textContent = state.evidence.memory.state;
  $("#competenceProjected").textContent = `${state.evidence.competence.projected} projected`;
  $("#competenceConsidered").textContent = state.evidence.competence.considered;
  $("#competenceProjectedCount").textContent = state.evidence.competence.projected;
  $("#competenceConsideredBar").style.width = state.evidence.competence.considered ? "100%" : "0";
  $("#competenceProjectedBar").style.width = state.evidence.competence.considered ? `${Math.min(100, state.evidence.competence.projected / state.evidence.competence.considered * 100)}%` : "0";
  $("#competenceState").textContent = state.evidence.competence.state;
  const evidenceCounts = [state.evidence.verified, state.evidence.supported, state.evidence.unknown, state.evidence.contradicted].map(Number);
  const evidenceTotal = evidenceCounts.reduce((sum, value) => sum + value, 0);
  $("#evidenceTotal").textContent = evidenceTotal;
  if (!evidenceTotal) {
    $("#evidenceDonut").style.background = "conic-gradient(#20344e 0 100%)";
  } else {
    const cuts = evidenceCounts.reduce((items, value) => [...items, (items.at(-1) || 0) + value / evidenceTotal * 100], []);
    $("#evidenceDonut").style.background = `conic-gradient(#249fff 0 ${cuts[0]}%, #23e8ff ${cuts[0]}% ${cuts[1]}%, #8b5cff ${cuts[1]}% ${cuts[2]}%, #ff5e7a ${cuts[2]}% 100%)`;
  }
  $("#contextState").textContent = state.context.state;
  $("#contextDetail").textContent = `${state.context.projected_items || 0} projected items · ${state.context.token_estimate ?? "—"} estimated tokens`;
  $("#contextPreview").textContent = state.context.projection ? JSON.stringify(state.context.projection, null, 2) : "";
  $("#contextMetric").textContent = state.context.token_estimate ?? "—";
  $("#trajectoryLog").textContent = JSON.stringify(state.trajectory, null, 2);
  applyTelemetry(state.telemetry);
}

async function stop() {
  if (!state.session) return;
  try {
    await api(`/v1/sessions/${state.session.session_id}/interrupt`, { method: "POST", body: "{}" });
    $("#sessionState").textContent = "CANCELLING";
    setCoreState("interrupt", "CANCELLING", "Stopping provider and agent loop");
  } catch (error) { toast(error.message, true); }
}

async function openModels() {
  state.provider = state.session?.provider || state.settings.selected_provider || "openai";
  $("#providerFilter").value = state.provider;
  $("#modelDialog").showModal();
  await loadModels(false);
}

async function loadModels(refresh = false) {
  state.provider = $("#providerFilter").value;
  state.sort = $("#modelSort").value;
  $("#modelStatus").textContent = "DISCOVERING LIVE MODELS…";
  try {
    const value = await api(`/v1/providers/${state.provider}/models?refresh=${refresh ? "true" : "false"}&sort=${encodeURIComponent(state.sort)}`);
    state.models = value.models;
    $("#modelStatus").textContent = `${state.models.length} models · ${value.cached ? (value.stale ? "STALE CACHE" : "CACHED") : "LIVE CATALOG"}${value.error ? ` · ${value.error.state}` : ""}`;
    renderModels();
  } catch (error) {
    state.models = [];
    $("#modelStatus").textContent = error.message;
    renderModels();
    toast(error.message, true);
  }
}

function modelMatches(model) {
  const query = $("#modelSearch").value.trim().toLowerCase();
  if (query && !`${model.display_name} ${model.model_id}`.toLowerCase().includes(query)) return false;
  if (state.filter === "free" && !model.free) return false;
  if (state.filter === "tools" && model.supports_tools !== true) return false;
  if (state.filter === "vision" && model.supports_vision !== true) return false;
  if (state.filter === "reasoning" && model.supports_reasoning !== true) return false;
  return true;
}

function price(model) {
  if (model.free) return "FREE";
  const pricing = model.pricing || {};
  if (pricing.prompt === undefined && pricing.completion === undefined) return "—";
  return `${pricing.prompt ?? "—"} / ${pricing.completion ?? "—"}`;
}

function renderModels() {
  const rows = state.models.filter(modelMatches);
  $("#modelList").innerHTML = rows.map(model => `<button class="model-row" data-index="${state.models.indexOf(model)}"><span><strong>${escapeHtml(model.display_name)} ${model.free ? '<em class="badge free">FREE</em>' : ""}</strong><small>${escapeHtml(model.model_id)}</small></span><span class="meta">CTX<br>${model.context_length ? Number(model.context_length).toLocaleString() : "—"}</span><span class="meta">TOOLS<br>${model.supports_tools === true ? "✓" : model.supports_tools === false ? "✕" : "UNKNOWN"}</span><span class="meta">PRICE<br>${escapeHtml(price(model))}</span></button>`).join("") || '<p class="muted">No models match this view. You may enter an exact identifier.</p>';
  $("#modelList").querySelectorAll("[data-index]").forEach(button => button.onclick = () => selectModel(state.models[Number(button.dataset.index)]));
}

async function selectModel(model) {
  if (!state.session) await newConversation();
  if (state.session.model_id && (state.session.model_id !== model.model_id || state.session.provider !== model.provider)) {
    if (!confirm(`Change reasoning engine?\n\nCurrent: ${modelLabel()}\nNew: ${providerLabel(model.provider)} / ${model.model_id}\n\nCortex continuity will be preserved. Provider/model provenance will change.`)) return;
  }
  state.session = await api(`/v1/sessions/${state.session.session_id}/model`, { method: "POST", body: JSON.stringify({ provider: model.provider, model_id: model.model_id }) });
  state.settings = await api("/v1/settings", { method: "PATCH", body: JSON.stringify({ selected_provider: model.provider, selected_model: model.model_id }) });
  state.selectedDescriptor = model;
  $("#modelDialog").close();
  updateHeader();
  renderSessions();
  setCoreState("idle", "READY", `${providerLabel(model.provider)} / ${model.model_id}`);
  toast(`${model.display_name} selected.${model.supports_tools === false ? " Agent tools are unavailable with this model." : ""}`);
}

async function manualModel() {
  const id = $("#modelSearch").value.trim();
  if (!id) return toast("Enter the exact provider model ID in search.", true);
  await selectModel({ provider: state.provider, model_id: id, display_name: id, supports_tools: null, free: id === "openrouter/free" || id.endsWith(":free") });
}

function applyAppearance(value) {
  document.body.classList.toggle("reduced-glow", value === "reduced");
  $$('[data-appearance]').forEach(button => button.classList.toggle("active", button.dataset.appearance === value));
}

function showCortex() {
  const evidence = state.evidence || {};
  const context = state.context || {};
  $("#cortexSummary").innerHTML = [
    ["Context projection", context.state || "INACTIVE"],
    ["Continuity", state.session ? "ACTIVE" : "INACTIVE"],
    ["Memory", `${evidence.memory?.projected || 0} items projected`],
    ["Competence", `${evidence.competence?.projected || 0} verified items`],
    ["Evidence capture", evidence.trajectory === "SEALED" ? "ACTIVE" : "PENDING"],
    ["Trajectory", evidence.trajectory || "UNSEALED"],
    ["Reasoning engine", modelLabel()],
    ["Host mutation", "FALSE"],
    ["Execution authority", "FALSE"],
  ].map(([label, value]) => `<div class="summary-row"><span>${label}</span><b>${escapeHtml(value)}</b></div>`).join("");
  $("#cortexDialog").showModal();
}

async function archiveCurrent() {
  if (!state.session) return;
  if (!confirm("Archive this local Cortex conversation? Its canonical trajectory evidence will remain intact.")) return;
  await api(`/v1/sessions/${state.session.session_id}/archive`, { method: "POST", body: "{}" });
  state.sessions = state.sessions.filter(session => session.session_id !== state.session.session_id);
  state.session = null;
  if (state.source) state.source.close();
  renderSessions(); renderMessages(); updateHeader();
  toast("Conversation archived locally.");
}

$("#composer").onsubmit = event => {
  event.preventDefault();
  const input = $("#prompt");
  const text = input.value.trim();
  if (text) { input.value = ""; input.style.height = "auto"; send(text); }
};
$("#prompt").onkeydown = event => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#composer").requestSubmit(); }
  if (event.key === "Escape") stop();
};
$("#prompt").oninput = event => { event.target.style.height = "auto"; event.target.style.height = `${Math.min(event.target.scrollHeight, 190)}px`; };
$("#stopButton").onclick = stop;
$("#archiveButton").onclick = archiveCurrent;
$("#retryButton").onclick = () => state.lastPrompt && send(state.lastPrompt);
$("#newConversation").onclick = newConversation;
$("#settingsButton").onclick = () => $("#settingsDialog").showModal();
$("#modelButton").onclick = openModels;
$("#closeModels").onclick = () => $("#modelDialog").close();
$("#refreshModels").onclick = () => loadModels(true);
$("#providerFilter").onchange = () => loadModels(false);
$("#modelSort").onchange = () => loadModels(true);
$("#modelSearch").oninput = renderModels;
$("#manualModel").onclick = manualModel;
$$('[data-filter]').forEach(button => button.onclick = () => {
  state.filter = button.dataset.filter;
  $$('[data-filter]').forEach(item => item.classList.toggle("active", item === button));
  renderModels();
});
$$('[data-side-tab]').forEach(button => button.onclick = () => {
  $$('[data-side-tab]').forEach(item => item.classList.toggle("active", item === button));
  $$(".side-view").forEach(item => item.classList.remove("active"));
  $(`#side${button.dataset.sideTab[0].toUpperCase() + button.dataset.sideTab.slice(1)}`).classList.add("active");
});
$$('[data-operator-tab]').forEach(button => button.onclick = () => {
  $$('[data-operator-tab]').forEach(item => item.classList.toggle("active", item === button));
  $$("#operatorBody > div, #operatorBody > pre").forEach(item => item.classList.add("hidden"));
  $(`#${button.dataset.operatorTab}Log`).classList.remove("hidden");
});
$("#drawerToggle").onclick = () => $("#operatorDrawer").classList.add("expanded");
$("#drawerClose").onclick = () => $("#operatorDrawer").classList.remove("expanded");
$("#sessionToggle").onclick = () => $("#sessionPopover").classList.toggle("hidden");
$("#cortexUsed").onclick = showCortex;
$("#closeCortex").onclick = () => $("#cortexDialog").close();
$$('[data-appearance]').forEach(button => button.onclick = async () => {
  applyAppearance(button.dataset.appearance);
  state.settings = await api("/v1/settings", { method: "PATCH", body: JSON.stringify({ appearance: button.dataset.appearance }) });
});
function renderUptime() {
  const elapsed = Math.max(0, state.uptimeBase + (Date.now() - state.uptimeStartedAt) / 1000);
  const hours = Math.floor(elapsed / 3600).toString().padStart(2, "0");
  const minutes = Math.floor(elapsed % 3600 / 60).toString().padStart(2, "0");
  const seconds = Math.floor(elapsed % 60).toString().padStart(2, "0");
  $("#uptimeMetric").textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(renderUptime, 1000);
window.addEventListener("resize", drawCharts);
loadInitial();
