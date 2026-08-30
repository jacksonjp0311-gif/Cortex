const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const state = {
  status: null,
  providers: [],
  tools: [],
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
  streamChunks: 0,
  toolCalls: 0,
  rateHistory: [],
  latencyHistory: [],
  uptimeBase: 0,
  uptimeStartedAt: Date.now(),
  eventSequence: 0,
  eventConnected: false,
  reconciling: false,
  campaignControl: null,
  campaigns: [],
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
  context.strokeStyle = "rgba(84, 132, 169, .24)";
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
  if (values.length === 1) {
    const gradient = context.createLinearGradient(0, 0, rect.width, 0);
    gradient.addColorStop(0, startColor);
    gradient.addColorStop(1, endColor);
    context.fillStyle = gradient;
    context.shadowBlur = 10;
    context.shadowColor = endColor;
    context.beginPath();
    context.arc(rect.width * .5, rect.height * .48, 3.2, 0, Math.PI * 2);
    context.fill();
    return;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, Math.abs(max) * .08, 1);
  const gradient = context.createLinearGradient(0, 0, rect.width, 0);
  gradient.addColorStop(0, startColor);
  gradient.addColorStop(1, endColor);
  context.strokeStyle = gradient;
  context.lineWidth = 2.6;
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
  ["confidenceChart", "cpuChart", "gpuChart", "networkChart"].forEach(id => {
    drawSparkline($(`#${id}`), [], "#249fff", "#23e8ff");
  });
  drawSparkline($("#healthChart"), state.streaming ? [1, 1, 1, 1] : [1], "#23e8ff", "#55ddb2");
}

const plasmaParticles = Array.from({ length: 92 }, (_, index) => ({
  phase: (index * 2.399963) % (Math.PI * 2),
  radius: .54 + ((index * 37) % 100) / 100 * 1.08,
  speed: .16 + ((index * 17) % 31) / 100,
  size: .45 + ((index * 29) % 17) / 12,
  tilt: .48 + ((index * 13) % 24) / 100,
}));

function coreEnergy() {
  return ({ idle: .28, context: .58, thinking: .72, streaming: 1, tool: .86, interrupt: .06, error: .5 })[document.body.dataset.coreState] ?? .28;
}

function drawCorePlasma(now) {
  const canvas = $("#corePlasmaCanvas");
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const pixelWidth = Math.max(1, Math.round(rect.width * dpr));
  const pixelHeight = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }
  const context = canvas.getContext("2d");
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, rect.width, rect.height);
  const reduced = document.body.classList.contains("reduced-glow") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  const time = reduced ? 0 : now / 1000;
  const energy = coreEnergy();
  const pulse = .5 + .5 * Math.sin(time * (1.6 + energy * 2.8));
  const cx = rect.width / 2;
  const cy = rect.height * .52;
  const radius = Math.min(rect.height * .405, rect.width * .205);
  context.globalCompositeOperation = "lighter";

  for (let band = 0; band < 5; band += 1) {
    const gradient = context.createLinearGradient(cx - radius, cy, cx + radius, cy);
    gradient.addColorStop(0, `rgba(30,128,255,${.1 + energy * .08})`);
    gradient.addColorStop(.46, `rgba(74,237,255,${.36 + energy * .18})`);
    gradient.addColorStop(.62, `rgba(174,91,255,${.34 + energy * .2})`);
    gradient.addColorStop(1, "rgba(28,113,255,.08)");
    context.strokeStyle = gradient;
    context.lineWidth = .8 + band * .34 + energy * .7;
    context.shadowBlur = 8 + energy * 13;
    context.shadowColor = band % 2 ? "#9669ff" : "#32dfff";
    context.beginPath();
    for (let step = 0; step <= 128; step += 1) {
      const angle = step / 128 * Math.PI * 2;
      const turbulence = Math.sin(angle * (3 + band) + time * (1.1 + band * .16)) * radius * (.025 + energy * .018)
        + Math.sin(angle * 11 - time * 1.7 + band) * radius * .012;
      const localRadius = radius * (.48 + band * .105) + turbulence;
      const x = cx + Math.cos(angle + time * (.018 + band * .008)) * localRadius;
      const y = cy + Math.sin(angle) * localRadius * (.57 + band * .035);
      if (step === 0) context.moveTo(x, y); else context.lineTo(x, y);
    }
    context.closePath();
    context.stroke();
  }

  for (let ray = 0; ray < 18; ray += 1) {
    const angle = ray / 18 * Math.PI * 2 + time * (.05 + energy * .06);
    const reach = radius * (1.08 + ((ray * 11) % 7) / 12 + pulse * energy * .13);
    context.beginPath();
    for (let step = 0; step <= 16; step += 1) {
      const progress = step / 16;
      const bend = Math.sin(progress * Math.PI * (2 + ray % 3) + time * 2.2 + ray) * radius * .055 * energy;
      const r = radius * .23 + (reach - radius * .23) * progress;
      const x = cx + Math.cos(angle) * r + Math.cos(angle + Math.PI / 2) * bend;
      const y = cy + Math.sin(angle) * r * .62 + Math.sin(angle + Math.PI / 2) * bend * .62;
      if (step === 0) context.moveTo(x, y); else context.lineTo(x, y);
    }
    context.strokeStyle = ray % 3 === 0
      ? `rgba(184,104,255,${.1 + energy * .24})`
      : `rgba(48,211,255,${.08 + energy * .22})`;
    context.lineWidth = ray % 4 === 0 ? 1.4 : .7;
    context.shadowBlur = 10 + energy * 12;
    context.shadowColor = ray % 3 === 0 ? "#a865ff" : "#32d9ff";
    context.stroke();
  }

  for (let arc = 0; arc < 24; arc += 1) {
    const ringRadius = radius * (1.12 + (arc % 4) * .11);
    const start = arc * .71 + time * (arc % 2 ? -.18 : .24) * (1 + energy);
    const length = .045 + ((arc * 7) % 10) / 90;
    context.beginPath();
    context.ellipse(cx, cy, ringRadius, ringRadius * .62, 0, start, start + length);
    context.strokeStyle = arc % 3 === 0 ? "rgba(165,102,255,.62)" : "rgba(55,213,255,.55)";
    context.lineWidth = arc % 5 === 0 ? 2.2 : 1;
    context.shadowBlur = 7;
    context.stroke();
  }

  plasmaParticles.forEach((particle, index) => {
    const angle = particle.phase + time * particle.speed * (.5 + energy);
    const radialPulse = 1 + Math.sin(time * 1.8 + index) * .025 * energy;
    const particleRadius = radius * particle.radius * radialPulse;
    const x = cx + Math.cos(angle) * particleRadius;
    const y = cy + Math.sin(angle) * particleRadius * particle.tilt;
    const alpha = .16 + energy * .46 * (.45 + .55 * Math.sin(angle * 3 + index) ** 2);
    context.fillStyle = index % 4 === 0 ? `rgba(185,119,255,${alpha})` : `rgba(85,225,255,${alpha})`;
    context.shadowBlur = 7 + energy * 8;
    context.shadowColor = index % 4 === 0 ? "#a86cff" : "#42ddff";
    context.beginPath();
    context.arc(x, y, particle.size * (1 + energy * .45), 0, Math.PI * 2);
    context.fill();
  });

  const coreGradient = context.createRadialGradient(cx, cy, 0, cx, cy, radius * .22);
  coreGradient.addColorStop(0, `rgba(255,255,255,${.92 - energy * .08})`);
  coreGradient.addColorStop(.18, `rgba(120,243,255,${.72 + pulse * .2})`);
  coreGradient.addColorStop(.56, `rgba(77,122,255,${.22 + energy * .2})`);
  coreGradient.addColorStop(1, "rgba(122,69,255,0)");
  context.fillStyle = coreGradient;
  context.shadowBlur = 28 + energy * 25;
  context.shadowColor = "#63e8ff";
  context.beginPath();
  context.arc(cx, cy, radius * (.18 + pulse * energy * .025), 0, Math.PI * 2);
  context.fill();
  context.globalCompositeOperation = "source-over";
  requestAnimationFrame(drawCorePlasma);
}

requestAnimationFrame(drawCorePlasma);

function resetLiveMetrics() {
  state.callStartedAt = performance.now();
  state.firstDeltaAt = null;
  state.streamedCharacters = 0;
  state.streamChunks = 0;
  state.toolCalls = 0;
  for (const [valueId, classId, label] of [
    ["#inputTokenMetric", "#inputTokenClass", "AWAITING PROVIDER"],
    ["#outputTokenMetric", "#outputTokenClass", "AWAITING PROVIDER"],
    ["#totalTokenMetric", "#totalTokenClass", "AWAITING PROVIDER"],
    ["#totalLatencyMetric", "#totalLatencyClass", "MEASURING"],
    ["#contextProjectionMetric", "#contextProjectionClass", "MEASURING"],
  ]) {
    $(valueId).textContent = "—";
    $(classId).textContent = label;
  }
  $("#rateClass").textContent = $("#tokenRate").textContent === "—" ? "AWAITING USAGE" : "LAST TURN · AWAITING LIVE";
  $("#latencyClass").textContent = $("#latencyMetric").textContent === "—" ? "MEASURING" : "LAST TURN · MEASURING";
  $("#toolMetric").textContent = "0";
  $("#streamChunkMetric").textContent = "0";
  $("#streamChunkClass").textContent = "MEASURED LIVE";
  $("#firstTokenMetric").textContent = "—";
  $("#firstTokenClass").textContent = "AWAITING FIRST DELTA";
  $("#callMetricState").textContent = "LIVE";
  $("#costClass").textContent = $("#costMetric").textContent === "—" ? "UNAVAILABLE" : "LAST TURN";
  $("#telemetryState").textContent = "LIVE";
  $("#healthMetric").textContent = "ACTIVE";
}

function updateLiveDelta(payload) {
  const elapsedMs = Number(payload.elapsed_ms) || (performance.now() - state.callStartedAt);
  state.streamedCharacters = Number(payload.streamed_characters) || (state.streamedCharacters + String(payload.text || "").length);
  state.streamChunks += 1;
  $("#streamChunkMetric").textContent = state.streamChunks;
  if (!state.firstDeltaAt) {
    state.firstDeltaAt = elapsedMs;
    $("#firstTokenMetric").textContent = elapsedMs.toFixed(0);
    $("#firstTokenClass").textContent = "MEASURED";
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
  setMetric("#inputTokenMetric", "#inputTokenClass", metrics.input_tokens, value => Number(value).toLocaleString());
  setMetric("#outputTokenMetric", "#outputTokenClass", metrics.output_tokens, value => Number(value).toLocaleString());
  setMetric("#totalTokenMetric", "#totalTokenClass", metrics.total_tokens, value => Number(value).toLocaleString());
  setMetric("#firstTokenMetric", "#firstTokenClass", metrics.first_token_latency, value => `${Number(value).toFixed(0)} ms`);
  setMetric("#totalLatencyMetric", "#totalLatencyClass", metrics.total_latency, value => `${Number(value).toFixed(0)} ms`);
  setMetric("#contextProjectionMetric", "#contextProjectionClass", metrics.context_projection_latency, value => `${Number(value).toFixed(0)} ms`);
  setMetric("#streamChunkMetric", "#streamChunkClass", metrics.stream_chunks, value => Number(value).toLocaleString());
  setMetric("#contextLoad", "#contextClass", metrics.context_tokens, value => Number(value).toLocaleString());
  setMetric("#costMetric", "#costClass", metrics.cost, value => Number(value).toPrecision(4));
  if (telemetry?.state === "STREAMING") {
    for (const [metricName, classId, pendingLabel] of [
      ["input_tokens", "#inputTokenClass", "AWAITING PROVIDER"],
      ["output_tokens", "#outputTokenClass", "AWAITING PROVIDER"],
      ["total_tokens", "#totalTokenClass", "AWAITING PROVIDER"],
      ["first_token_latency", "#firstTokenClass", "AWAITING FIRST DELTA"],
      ["total_latency", "#totalLatencyClass", "MEASURING"],
      ["context_projection_latency", "#contextProjectionClass", "MEASURING"],
    ]) {
      if (metrics[metricName]?.value == null) $(classId).textContent = pendingLabel;
    }
  }
  $("#toolMetric").textContent = metrics.tool_calls?.value ?? 0;
  $("#toolMetricClass").textContent = measurementLabel(metrics.tool_calls?.measurement);
  $("#callMetricState").textContent = telemetry?.state || "NO TURN";
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

function renderToolCatalog() {
  const card = document.querySelector(".appearance-card");
  if (!card) return;
  let root = $("#toolCatalog");
  if (!root) {
    root = document.createElement("div");
    root.id = "toolCatalog";
    root.className = "tool-catalog";
    card.insertBefore(root, card.querySelector(".segmented"));
  }
  root.innerHTML = state.tools.map(tool => `<div class="tool-manifest"><span><strong>${escapeHtml(tool.tool_id)}</strong><small>v${escapeHtml(tool.version)} · ${escapeHtml(tool.authority_class)}</small></span><code>${escapeHtml(tool.manifest_hash.slice(0, 12))}</code></div>`).join("") || '<span class="muted">No host tools registered.</span>';
}

async function loadInitial() {
  try {
    state.status = await api("/v1/status");
    renderAutonomy();
    state.uptimeBase = Number(state.status.uptime_seconds || 0);
    state.uptimeStartedAt = Date.now();
    state.settings = await api("/v1/settings");
    state.tools = (await api("/v1/tools")).tools;
    renderToolCatalog();
    await loadProviders();
    state.sessions = (await api("/v1/sessions")).sessions;
    renderSessions();
    applyAppearance(state.settings.appearance || "standard");
    $$('[data-tool-mode]').forEach(button => button.classList.toggle("active", button.dataset.toolMode === (state.settings.default_tool_mode || "proposal")));
    drawCharts();
    if (state.sessions.length) await openSession(state.sessions[0].session_id);
    else if (!state.providers.some(provider => provider.configured)) $("#settingsDialog").showModal();
  } catch (error) { toast(error.message, true); setCoreState("error", "OFFLINE", "Cortex service unavailable"); }
}

function renderAutonomy() {
  const autonomy = state.status?.autonomy || {};
  $("#autonomyState").textContent = String(autonomy.state || "UNKNOWN").replaceAll("_", " ");
  const tournamentCount = autonomy.ledger?.tournament_count;
  const campaignState = String(autonomy.improvement_campaigns || "UNKNOWN").replaceAll("_", " ");
  $("#autonomyCampaigns").textContent = Number.isInteger(tournamentCount) ? `${campaignState} · ${tournamentCount} TOURNAMENTS` : campaignState;
  $("#autonomyPromotion").textContent = String(autonomy.automatic_promotion || "UNKNOWN").replaceAll("_", " ");
  $("#autonomyRollback").textContent = String(autonomy.canary_rollback || "UNKNOWN").replaceAll("_", " ");
  $("#autonomyModelAuthority").textContent = autonomy.model_may_self_authorize === false ? "NONE" : "UNKNOWN";
}

async function loadCampaigns() {
  const surface = await api("/v1/campaigns");
  state.campaigns = surface.campaigns || [];
  const root = $("#campaignRows");
  root.innerHTML = state.campaigns.map(campaign => {
    const prepared = campaign.integration_preparation;
    const integrated = campaign.integration_result;
    const rollback = campaign.rollback;
    const lifecycle = campaign.status === "prepared_request"
      ? '<button data-campaign-command="start">START</button><button data-campaign-command="cancel">CANCEL</button>'
      : campaign.status === "start_requested"
        ? '<button data-campaign-command="cancel">CANCEL</button>' : "";
    const integration = prepared && !integrated
      ? '<button data-campaign-command="integrate">INTEGRATE</button>' : "";
    const recovery = integrated && !rollback
      ? '<button data-campaign-command="rollback">ROLL BACK</button>' : "";
    return `<article class="campaign-row" data-campaign="${escapeHtml(campaign.campaign_id)}"><div><strong>${escapeHtml(campaign.campaign_id)}</strong><small>${escapeHtml(campaign.status || "UNKNOWN")} · STATE ${escapeHtml(campaign.state_sequence ?? "—")}</small></div><code>${escapeHtml(String(campaign.state_receipt_hash || "").slice(0, 16))}</code><div>${lifecycle}${integration}${recovery}</div></article>`;
  }).join("") || '<p class="muted">No canonical campaigns.</p>';
  root.querySelectorAll("[data-campaign-command]").forEach(button => {
    button.onclick = () => runCampaignCommand(button.closest("[data-campaign]").dataset.campaign, button.dataset.campaignCommand);
  });
}

function campaignHeaders() {
  if (!state.campaignControl) throw new Error("Authenticate host control first.");
  return {
    "Authorization": `Bearer ${state.campaignControl.control_token}`,
    "X-Cortex-Control-Session": state.campaignControl.receipt_hash,
    "X-Cortex-CSRF": state.campaignControl.csrf_token,
    "X-Cortex-Action-Nonce": crypto.randomUUID(),
  };
}

async function authenticateCampaignControl() {
  const principal_id = $("#campaignPrincipal").value.trim();
  const principal_secret = $("#campaignSecret").value;
  if (!principal_id || !principal_secret) return toast("Principal ID and secret are required.", true);
  try {
    state.campaignControl = await api("/v1/control/sessions", {
      method: "POST",
      body: JSON.stringify({
        principal_id,
        principal_secret,
        allowed_actions: ["campaign.prepare", "campaign.start", "campaign.cancel", "campaign.promote", "campaign.integrate", "campaign.rollback"],
      }),
    });
    $("#campaignSecret").value = "";
    $("#campaignControlState").textContent = "AUTHENTICATED · EPHEMERAL";
    toast("Campaign control authenticated. Tokens remain in browser memory only.");
  } catch (error) { state.campaignControl = null; $("#campaignControlState").textContent = "LOCKED"; toast(error.message, true); }
}

async function runCampaignCommand(campaignId, command, explicit = {}) {
  try {
    const campaign = state.campaigns.find(item => item.campaign_id === campaignId) || {};
    const body = { ...explicit };
    if (command === "integrate") body.preparation_receipt_hash = campaign.integration_preparation?.receipt_hash || "";
    if (command === "rollback") body.integration_result_hash = campaign.integration_result?.receipt_hash || "";
    await api(`/v1/campaigns/${encodeURIComponent(campaignId)}/${command}`, {
      method: "POST", headers: campaignHeaders(), body: JSON.stringify(body),
    });
    toast(`${campaignId}: ${command} recorded canonically.`);
    await loadCampaigns();
  } catch (error) { toast(error.message, true); }
}

async function prepareCampaignFromUI() {
  const campaignId = $("#campaignId").value.trim();
  if (!campaignId) return toast("Campaign ID is required.", true);
  await runCampaignCommand(campaignId, "prepare", {
    policy_receipt_hash: $("#campaignPolicyHash").value.trim(),
    storm_summary_receipt_hash: $("#campaignStormHash").value.trim(),
  });
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
  const live = await api(`/v1/sessions/${id}/live`);
  state.eventSequence = Number(live.last_sequence || 0);
  state.eventConnected = false;
  state.streaming = Boolean(live.active);
  state.telemetry = live.telemetry;
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
  const sessionId = state.session.session_id;
  state.source = new EventSource(`/v1/events?session_id=${encodeURIComponent(sessionId)}&after=${state.eventSequence}`);
  state.source.onopen = () => {
    if (state.session?.session_id !== sessionId) return;
    state.eventConnected = true;
    $("#telemetryState").textContent = state.streaming ? "LIVE" : "STREAM CONNECTED";
    $("#sessionState").textContent = state.streaming ? "ACTIVE" : "READY";
  };
  state.source.addEventListener("cortex", event => handleEvent(JSON.parse(event.data)));
  state.source.onerror = () => {
    if (state.session?.session_id !== sessionId) return;
    state.eventConnected = false;
    $("#telemetryState").textContent = "RECONNECTING";
    if (state.streaming) $("#sessionState").textContent = "RECONNECTING";
    reconcileLiveState("event-stream-error");
  };
}

function handleEvent(event) {
  const sequence = Number(event.sequence || 0);
  if (sequence && sequence <= state.eventSequence) return;
  const gap = sequence && state.eventSequence && sequence > state.eventSequence + 1;
  if (sequence) state.eventSequence = sequence;
  if (gap) reconcileLiveState("event-gap");
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
    if (payload.duration_ms != null) {
      $("#contextProjectionMetric").textContent = `${Number(payload.duration_ms).toFixed(0)} ms`;
      $("#contextProjectionClass").textContent = "MEASURED";
    }
    scheduleIntelligenceRefresh();
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
    const input = usage.input_tokens ?? usage.prompt_tokens ?? usage.input;
    const output = usage.output_tokens ?? usage.completion_tokens ?? usage.output;
    const total = usage.total_tokens ?? usage.total ?? (Number.isFinite(Number(input)) && Number.isFinite(Number(output)) ? Number(input) + Number(output) : null);
    if (input != null) { $("#inputTokenMetric").textContent = Number(input).toLocaleString(); $("#inputTokenClass").textContent = "PROVIDER REPORTED"; }
    if (output != null) { $("#outputTokenMetric").textContent = Number(output).toLocaleString(); $("#outputTokenClass").textContent = "PROVIDER REPORTED"; }
    if (total != null) { $("#totalTokenMetric").textContent = Number(total).toLocaleString(); $("#totalTokenClass").textContent = "PROVIDER REPORTED"; }
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
    scheduleIntelligenceRefresh();
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
  if (type === "trajectory.sealed") {
    if (payload.total_latency_ms != null) {
      $("#totalLatencyMetric").textContent = `${Number(payload.total_latency_ms).toFixed(0)} ms`;
      $("#totalLatencyClass").textContent = "MEASURED";
    }
    scheduleIntelligenceRefresh();
  }
  if (type === "chat.interrupt.requested" || type === "model.interrupted") setCoreState("interrupt", "INTERRUPTED", "Operator cancellation received");
  if (type === "chat.turn.completed") {
    state.streaming = false;
    state.streamText = "";
    $("#telemetryState").textContent = "TURN COMPLETE";
    $("#healthMetric").textContent = payload.status === "interrupted" ? "STOPPED" : "HEALTHY";
    setCoreState("idle", payload.status === "interrupted" ? "STOPPED" : "SEALED", payload.status === "interrupted" ? "Generation interrupted" : "Trajectory recorded by Cortex");
    reloadCurrent().catch(error => toast(error.message, true));
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
  const authority = event.payload.authority_class ? ` · ${event.payload.authority_class}` : "";
  const manifest = event.payload.manifest_hash ? ` · ${event.payload.manifest_hash.slice(0, 12)}` : "";
  node.textContent = `${event.event_type} · ${event.payload.tool_name || event.payload.name || ""}${authority}${manifest} · ${event.payload.status || ""}${duration}`;
  root.prepend(node);
}

let intelligenceRefreshTimer = null;
function scheduleIntelligenceRefresh(delay = 120) {
  clearTimeout(intelligenceRefreshTimer);
  intelligenceRefreshTimer = setTimeout(() => {
    refreshIntelligence().catch(error => toast(error.message, true));
  }, delay);
}

async function reconcileLiveState(reason = "watchdog") {
  if (!state.session || state.reconciling) return;
  state.reconciling = true;
  const sessionId = state.session.session_id;
  try {
    const live = await api(`/v1/sessions/${sessionId}/live`);
    if (state.session?.session_id !== sessionId) return;
    const backendSequence = Number(live.last_sequence || 0);
    if (backendSequence < state.eventSequence) state.eventSequence = backendSequence;
    if (backendSequence > state.eventSequence) state.eventSequence = backendSequence;
    applyTelemetry(live.telemetry);
    if (live.active && !state.streaming) {
      state.streaming = true;
      state.callStartedAt ||= performance.now();
      setCoreState("thinking", "THINKING", "Recovered active Cortex turn");
      updateHeader();
    } else if (!live.active && state.streaming) {
      await reloadCurrent();
      $("#telemetryState").textContent = "RECOVERED · TURN COMPLETE";
      $("#healthMetric").textContent = "HEALTHY";
      setCoreState("idle", "SEALED", `Canonical state reconciled · ${reason}`);
      toast("Live view recovered from canonical Cortex state.");
    }
  } catch (error) {
    if (state.streaming) $("#sessionState").textContent = "RECONNECTING";
  } finally {
    state.reconciling = false;
  }
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
  [state.context, state.evidence, state.trajectory, state.telemetry, state.workspace] = await Promise.all([
    api(`/v1/sessions/${id}/context`), api(`/v1/sessions/${id}/evidence`),
    api(`/v1/sessions/${id}/trajectory`), api(`/v1/sessions/${id}/telemetry`),
    api(`/v1/sessions/${id}/workspace`),
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
  renderWorkspace();
  applyTelemetry(state.telemetry);
}

function renderWorkspace() {
  const root = $("#toolLog");
  root.querySelectorAll(".workspace-proposal").forEach(node => node.remove());
  for (const proposal of state.workspace?.proposals || []) {
    const card = document.createElement("article");
    card.className = "tool-unit workspace-proposal";
    const title = document.createElement("strong");
    title.textContent = `PATCH REVIEW · ${proposal.summary}`;
    const meta = document.createElement("p");
    meta.textContent = `${proposal.targets.join(", ")} · ${proposal.proposal_hash.slice(0, 16)}`;
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "INSPECT EXACT DIFF";
    const pre = document.createElement("pre");
    pre.textContent = proposal.patch;
    details.append(summary, pre);
    const approve = document.createElement("button");
    approve.type = "button";
    const verified = proposal.verification?.status === "verified";
    const trial = proposal.improvement_trial;
    const promotableTrial = ["REPAIR_MEASURED", "VERIFIED_MAINTENANCE"].includes(trial?.status);
    approve.textContent = proposal.application
      ? (proposal.application.targets_current ? "PROMOTED & VERIFIED" : "PROMOTED · TARGET DRIFT")
      : promotableTrial ? (trial.status === "REPAIR_MEASURED" ? "PROMOTE MEASURED REPAIR" : "PROMOTE VERIFIED MAINTENANCE")
      : trial ? `${trial.status.replaceAll("_", " ")} · BLOCKED`
      : verified ? "MEASURE AGAINST BASELINE" : proposal.verification ? "VERIFICATION HELD" : "APPROVE & VERIFY";
    approve.disabled = Boolean(proposal.application);
    if (!proposal.application && !proposal.verification) approve.onclick = () => verifyWorkspaceProposal(proposal, approve);
    if (!proposal.application && verified && !trial) approve.onclick = () => measureWorkspaceProposal(proposal, approve);
    if (!proposal.application && promotableTrial) approve.onclick = () => promoteWorkspaceProposal(proposal, approve);
    if (proposal.verification && !verified) approve.disabled = true;
    if (trial && !promotableTrial) approve.disabled = true;
    let comparison = null;
    if (trial) {
      comparison = document.createElement("p");
      const baseline = trial.arms?.baseline?.all_host_checks_pass ? "PASS" : "FAIL";
      const candidate = trial.arms?.candidate?.all_host_checks_pass ? "PASS" : "FAIL";
      comparison.textContent = `COUNTERFACTUAL · baseline ${baseline} → candidate ${candidate} · Δ ${trial.paired_effect}`;
      comparison.className = "muted";
    }
    card.append(title, meta, details);
    if (comparison) card.append(comparison);
    card.append(approve);
    root.prepend(card);
  }
}

async function verifyWorkspaceProposal(proposal, button) {
  if (!confirm(`Verify this exact Cortex patch in an isolated worktree?\n\n${proposal.summary}\n\nTargets: ${proposal.targets.join(", ")}\n\nThe active repository will not be changed. Verification may execute the reviewed candidate through host-selected checks.`)) return;
  button.disabled = true;
  button.textContent = "VERIFYING…";
  try {
    const result = await api(`/v1/sessions/${state.session.session_id}/workspace/verify`, {
      method: "POST",
      body: JSON.stringify({ proposal_hash: proposal.proposal_hash, approval_challenge: proposal.approval_challenge }),
    });
    button.textContent = result.status === "verified" ? "MEASURE AGAINST BASELINE" : "VERIFICATION HELD";
    toast(`Isolated verification ${result.status} · ${String(result.receipt_hash).slice(0, 16)}`, result.status !== "verified");
    await refreshIntelligence();
  } catch (error) {
    button.disabled = false;
    button.textContent = "APPROVE & VERIFY";
    toast(error.message, true);
  }
}

async function measureWorkspaceProposal(proposal, button) {
  if (!confirm(`Measure this verified change against an unchanged baseline from the same Git HEAD?\n\n${proposal.summary}\n\nBoth arms use the same host-frozen evaluator. The active repository will not be changed.`)) return;
  button.disabled = true;
  button.textContent = "MEASURING…";
  try {
    const result = await api(`/v1/sessions/${state.session.session_id}/workspace/trial`, {
      method: "POST",
      body: JSON.stringify({ proposal_hash: proposal.proposal_hash, approval_challenge: proposal.approval_challenge }),
    });
    toast(`Counterfactual result ${result.status} · baseline ${result.arms.baseline.all_host_checks_pass ? "PASS" : "FAIL"} → candidate ${result.arms.candidate.all_host_checks_pass ? "PASS" : "FAIL"}`, !["REPAIR_MEASURED", "VERIFIED_MAINTENANCE"].includes(result.status));
    await refreshIntelligence();
  } catch (error) {
    button.disabled = false;
    button.textContent = "MEASURE AGAINST BASELINE";
    toast(error.message, true);
  }
}

async function promoteWorkspaceProposal(proposal, button) {
  if (!confirm(`Promote this independently verified patch into the active checkout?\n\n${proposal.summary}\n\nThis is a second, explicit operator decision.`)) return;
  button.disabled = true;
  button.textContent = "PROMOTING…";
  try {
    const result = await api(`/v1/sessions/${state.session.session_id}/workspace/apply`, {
      method: "POST",
      body: JSON.stringify({
        proposal_hash: proposal.proposal_hash,
        approval_challenge: proposal.approval_challenge,
        verification_receipt_hash: proposal.verification.receipt_hash,
        improvement_result_hash: proposal.improvement_trial?.receipt_hash || "",
      }),
    });
    button.textContent = "PROMOTED & VERIFIED";
    toast(`Verified patch promoted · ${String(result.receipt_hash).slice(0, 16)}`);
    await refreshIntelligence();
  } catch (error) {
    button.disabled = false;
    button.textContent = proposal.improvement_trial?.status === "REPAIR_MEASURED" ? "PROMOTE MEASURED REPAIR" : "PROMOTE VERIFIED MAINTENANCE";
    toast(error.message, true);
  }
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
  if (button.dataset.operatorTab === "campaigns") loadCampaigns().catch(error => toast(error.message, true));
});
$("#campaignAuthenticate").onclick = authenticateCampaignControl;
$("#campaignRefresh").onclick = () => loadCampaigns().catch(error => toast(error.message, true));
$("#campaignPrepare").onclick = prepareCampaignFromUI;
$("#drawerToggle").onclick = () => $("#operatorDrawer").classList.add("expanded");
$("#drawerClose").onclick = () => $("#operatorDrawer").classList.remove("expanded");
$("#sessionToggle").onclick = () => $("#sessionPopover").classList.toggle("hidden");
$("#cortexUsed").onclick = showCortex;
$("#closeCortex").onclick = () => $("#cortexDialog").close();
$$('[data-appearance]').forEach(button => button.onclick = async () => {
  applyAppearance(button.dataset.appearance);
  state.settings = await api("/v1/settings", { method: "PATCH", body: JSON.stringify({ appearance: button.dataset.appearance }) });
});
$$('[data-tool-mode]').forEach(button => button.onclick = async () => {
  const mode = button.dataset.toolMode;
  $$('[data-tool-mode]').forEach(item => item.classList.toggle("active", item === button));
  state.settings = await api("/v1/settings", { method: "PATCH", body: JSON.stringify({ default_tool_mode: mode }) });
  toast(mode === "proposal" ? "Cortex may propose exact diffs. Only operator approval can apply them." : mode === "read_only" ? "Repository inspection enabled. Execution and writes remain blocked." : "Repository tools disabled.");
});
function renderUptime() {
  const elapsed = Math.max(0, state.uptimeBase + (Date.now() - state.uptimeStartedAt) / 1000);
  const hours = Math.floor(elapsed / 3600).toString().padStart(2, "0");
  const minutes = Math.floor(elapsed % 3600 / 60).toString().padStart(2, "0");
  const seconds = Math.floor(elapsed % 60).toString().padStart(2, "0");
  $("#uptimeMetric").textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(renderUptime, 1000);
setInterval(() => {
  if (!state.session) return;
  if (state.streaming && state.callStartedAt && !state.firstDeltaAt) {
    const elapsed = performance.now() - state.callStartedAt;
    $("#latencyMetric").textContent = elapsed.toFixed(0);
    $("#latencyClass").textContent = "LOCAL ELAPSED · AWAITING TOKEN";
  }
  if (state.streaming || !state.eventConnected) reconcileLiveState("watchdog");
}, 1000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) reconcileLiveState("page-resumed");
});
window.addEventListener("online", () => reconcileLiveState("network-restored"));
window.addEventListener("resize", drawCharts);
loadInitial();
