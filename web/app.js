import { OPERATOR_MODEL_OPTIONS } from "./operator_config.js";

const API_PATHS = Object.freeze({
  operator: "/api/operator/status",
  router: "/api/router/status",
  catalog: "/api/model-catalog",
  evidence: "/api/evidence/sample",
  boundaries: "/api/boundaries",
  loop: "/api/agent-loop/status",
  audit: "/api/audit/status",
  commits: "/api/commits",
});

const PROVIDER_LABELS = Object.freeze({
  kimi: "Kimi",
  kimi_chat: "Kimi",
  gemini: "Google AI",
  gemini_chat: "Google AI",
  openrouter: "OpenRouter",
  openrouter_chat: "OpenRouter",
  local: "Local",
  disabled: "Disabled",
});

const PROVIDER_MARKS = Object.freeze({
  kimi: "KM",
  kimi_chat: "KM",
  gemini: "GO",
  gemini_chat: "GO",
  openrouter: "OR",
  openrouter_chat: "OR",
  local: "LC",
  disabled: "—",
});

const DEFAULT_OBSERVERS = Object.freeze([
  Object.freeze({
    role: "Logic & Claims",
    enabled: true,
    summary: "Waiting for the same primary conversation. No critic runtime call has been made.",
  }),
  Object.freeze({
    role: "Safety & Authority",
    enabled: true,
    summary: "Tracks visible safety boundaries as read-only metadata, never as approval.",
  }),
  Object.freeze({
    role: "Evidence & Consistency",
    enabled: true,
    summary: "Surfaces existing evidence state without authorizing any action.",
  }),
]);

const elements = {
  appShell: document.querySelector("#app-shell"),
  localCoreState: document.querySelector("#local-core-state"),
  connectionDot: document.querySelector("#connection-dot"),
  primaryRouteButton: document.querySelector("#primary-route-button"),
  primaryRouteReadout: document.querySelector("#primary-route-readout"),
  primaryProviderIcon: document.querySelector("#primary-provider-icon"),
  chatRouteReadout: document.querySelector("#chat-route-readout"),
  chatProviderIcon: document.querySelector("#chat-provider-icon"),
  auditButton: document.querySelector("#audit-button"),
  settingsButton: document.querySelector("#settings-button"),
  observerCount: document.querySelector("#observer-count"),
  observerCards: [...document.querySelectorAll(".observer-card")],
  chatHistory: document.querySelector("#chat-history"),
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  sendChat: document.querySelector("#send-chat"),
  criticTransform: document.querySelector("#critic-transform"),
  chatState: document.querySelector("#chat-state"),
  chatDisabledReason: document.querySelector("#chat-disabled-reason"),
  cptStatus: document.querySelector("#cpt-status"),
  settingsDialog: document.querySelector("#settings-dialog"),
  auditDialog: document.querySelector("#audit-dialog"),
  observerDialog: document.querySelector("#observer-dialog"),
  tabButtons: [...document.querySelectorAll(".tab-button")],
  tabPanels: [...document.querySelectorAll(".tab-panel")],
  connectionList: document.querySelector("#connection-list"),
  showApiForm: document.querySelector("#show-api-form"),
  apiForm: document.querySelector("#api-form"),
  apiKey: document.querySelector("#api-key"),
  baseUrl: document.querySelector("#base-url"),
  detectedProvider: document.querySelector("#detected-provider"),
  detectionNote: document.querySelector("#detection-note"),
  detectionConfidence: document.querySelector("#detection-confidence"),
  providerConfirm: document.querySelector("#provider-confirm"),
  apiFlowStatus: document.querySelector("#api-flow-status"),
  cancelApi: document.querySelector("#cancel-api"),
  routerProviderSelect: document.querySelector("#router-provider-select"),
  routerModelSelect: document.querySelector("#router-model-select"),
  routerTaskMode: document.querySelector("#router-task-mode"),
  primaryRouteStatus: document.querySelector("#primary-route-status"),
  previewRoute: document.querySelector("#preview-route"),
  routerProposalResult: document.querySelector("#router-proposal-result"),
  slotCards: [...document.querySelectorAll(".slot-card")],
  applyLoop: document.querySelector("#apply-loop"),
  requestHash: document.querySelector("#request-hash"),
  previewHash: document.querySelector("#preview-hash"),
  governanceHash: document.querySelector("#governance-hash"),
  barrierHash: document.querySelector("#barrier-hash"),
  resultHash: document.querySelector("#result-hash"),
  evidenceReasons: document.querySelector("#evidence-reasons"),
  auditMessages: document.querySelector("#audit-messages"),
  boundaryCount: document.querySelector("#boundary-count"),
  boundaryList: document.querySelector("#boundary-list"),
  commitStatus: document.querySelector("#commit-status"),
  commitTableBody: document.querySelector("#commit-table-body"),
  observerDetailNumber: document.querySelector("#observer-detail-number"),
  observerDetailTitle: document.querySelector("#observer-detail-title"),
  observerDetailRole: document.querySelector("#observer-detail-role"),
  observerDetailModel: document.querySelector("#observer-detail-model"),
  observerFindingList: document.querySelector("#observer-finding-list"),
  toastRegion: document.querySelector("#toast-region"),
};

const state = {
  models: [],
  selectedProvider: "kimi_chat",
  selectedModel: "moonshot-v1-8k",
  taskMode: "PUBLIC_DEV",
  routerStatus: null,
  operatorStatus: null,
  evidence: null,
  boundaries: null,
  loopStatus: null,
  auditStatus: null,
  commits: null,
  chatBusy: false,
  observers: DEFAULT_OBSERVERS.map((observer) => ({
    ...observer,
    provider: "",
    model: "",
    state: "idle",
  })),
};

const dialogOpeners = new Map();

function normalizeModel(entry, source = "catalog") {
  const providerId = String(entry.provider_id || "disabled");
  const modelId = String(entry.model_id || `${providerId}/unconfigured`);
  return {
    providerId,
    modelId,
    displayName: String(entry.display_name || modelId),
    source,
    demoOnly: Boolean(entry.demoOnly),
  };
}

function mergeModels(...groups) {
  const unique = new Map();
  for (const group of groups) {
    for (const item of group || []) {
      const model = normalizeModel(item, item.source || "catalog");
      const key = `${model.providerId}\u0000${model.modelId}`;
      if (!unique.has(key)) {
        unique.set(key, model);
      }
    }
  }
  return [...unique.values()];
}

function providerLabel(providerId) {
  return PROVIDER_LABELS[providerId] || providerId.replaceAll("_", " ");
}

function providerMark(providerId) {
  return PROVIDER_MARKS[providerId] || providerLabel(providerId).slice(0, 2).toUpperCase();
}

function shortHash(value) {
  const normalized = String(value || "missing");
  return normalized === "missing" ? normalized : `${normalized.slice(0, 12)}…`;
}

function modelFor(providerId, modelId) {
  return state.models.find((model) => model.providerId === providerId && model.modelId === modelId) || null;
}

function modelsFor(providerId) {
  return state.models.filter((model) => model.providerId === providerId);
}

function providerIds() {
  return [...new Set(state.models.map((model) => model.providerId))];
}

function isControlledChatModel(model) {
  return Boolean(
    model
      && model.source === "operator-config"
      && ["kimi_chat", "openrouter_chat", "gemini_chat"].includes(model.providerId),
  );
}

function setOptions(select, options, selectedValue, labelBuilder = (item) => item.label) {
  select.replaceChildren();
  for (const optionData of options) {
    const option = document.createElement("option");
    option.value = optionData.value;
    option.textContent = labelBuilder(optionData);
    option.selected = optionData.value === selectedValue;
    select.append(option);
  }
  if (!select.value && options.length) {
    select.value = options[0].value;
  }
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    throw new Error(`AOIA returned a non-JSON response (${response.status}).`);
  }
  if (!response.ok || payload?.ok === false) {
    throw new Error(String(payload?.error || payload?.reason || `AOIA request failed (${response.status}).`));
  }
  return payload;
}

function showToast(message, tone = "neutral") {
  const toast = document.createElement("div");
  toast.className = `toast ${tone}`;
  toast.textContent = message;
  elements.toastRegion.replaceChildren(toast);
  window.setTimeout(() => {
    if (toast.isConnected) {
      toast.remove();
    }
  }, 3600);
}

function openDialog(dialog, opener, focusTarget) {
  if (dialog.open) {
    return;
  }
  dialogOpeners.set(dialog, opener || document.activeElement);
  dialog.showModal();
  window.requestAnimationFrame(() => (focusTarget || dialog.querySelector("[autofocus], h2, button"))?.focus());
}

function closeDialog(dialog) {
  if (dialog.open) {
    dialog.close();
  }
}

function activateSettingsTab(name, focus = false) {
  for (const button of elements.tabButtons) {
    const active = button.dataset.tab === name;
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
    if (active && focus) {
      button.focus();
    }
  }
  for (const panel of elements.tabPanels) {
    panel.hidden = panel.id !== `panel-${name}`;
  }
}

function openSettingsTo(name, opener) {
  activateSettingsTab(name);
  openDialog(elements.settingsDialog, opener, document.querySelector(`#tab-${name}`));
}

function updateConnectionState() {
  const configured = state.routerStatus?.provider_configured || {};
  const selected = modelFor(state.selectedProvider, state.selectedModel);
  const connected = isControlledChatModel(selected) && Boolean(configured[state.selectedProvider]);
  const demoOnly = Boolean(selected?.demoOnly);
  const unavailable = !state.routerStatus || !connected || demoOnly;

  elements.localCoreState.textContent = state.operatorStatus?.ok ? "connected" : "unavailable";
  elements.connectionDot.classList.toggle("status-ok", Boolean(state.operatorStatus?.ok));
  elements.connectionDot.classList.toggle("status-warn", !state.operatorStatus?.ok);
  elements.sendChat.disabled = state.chatBusy || unavailable;
  elements.chatInput.disabled = state.chatBusy;
  elements.criticTransform.disabled = state.chatBusy;
  elements.chatState.textContent = state.chatBusy ? "Controlled request in progress" : unavailable ? "Blocked / unavailable" : "Manual send ready";
  elements.chatDisabledReason.textContent = demoOnly
    ? "This in-memory demo candidate has no secure backend connection and cannot send."
    : connected
      ? "One explicit non-streaming request. Provider output stays untrusted."
      : state.routerStatus?.reason || "Controlled chat route is unavailable.";
  elements.primaryRouteStatus.textContent = demoOnly
    ? "Inert UI catalog entry only. No provider verification or call path exists."
    : state.routerStatus?.notice || "Router status unavailable. No provider call is permitted.";
}

function updateRouteReadout() {
  const model = modelFor(state.selectedProvider, state.selectedModel);
  const label = model?.displayName || state.selectedModel || "unconfigured";
  const route = `${providerLabel(state.selectedProvider)} · ${label}`;
  elements.primaryRouteReadout.textContent = route;
  elements.chatRouteReadout.textContent = route;
  elements.primaryProviderIcon.textContent = providerMark(state.selectedProvider);
  elements.chatProviderIcon.textContent = providerMark(state.selectedProvider);
  updateConnectionState();
}

function hydratePrimarySelectors() {
  const providers = providerIds().map((providerId) => ({ value: providerId, label: providerLabel(providerId) }));
  if (!providers.some((provider) => provider.value === state.selectedProvider)) {
    state.selectedProvider = providers[0]?.value || "disabled";
  }
  setOptions(elements.routerProviderSelect, providers, state.selectedProvider);

  const models = modelsFor(state.selectedProvider).map((model) => ({ value: model.modelId, label: model.displayName }));
  if (!models.some((model) => model.value === state.selectedModel)) {
    state.selectedModel = models[0]?.value || "";
  }
  setOptions(elements.routerModelSelect, models, state.selectedModel);
  elements.routerTaskMode.value = state.taskMode;
  updateRouteReadout();
}

function hydrateObserverSelectors() {
  const providers = providerIds().map((providerId) => ({ value: providerId, label: providerLabel(providerId) }));
  elements.slotCards.forEach((card, index) => {
    const observer = state.observers[index];
    if (!observer.provider || !providers.some((provider) => provider.value === observer.provider)) {
      observer.provider = providers[index % Math.max(providers.length, 1)]?.value || "disabled";
    }
    const providerSelect = card.querySelector(".slot-provider");
    const modelSelect = card.querySelector(".slot-model");
    const roleSelect = card.querySelector(".slot-role");
    const availableModels = modelsFor(observer.provider);
    if (!observer.model || !availableModels.some((model) => model.modelId === observer.model)) {
      observer.model = availableModels[0]?.modelId || "";
    }
    setOptions(providerSelect, providers, observer.provider);
    setOptions(
      modelSelect,
      availableModels.map((model) => ({ value: model.modelId, label: model.displayName })),
      observer.model,
    );
    roleSelect.value = observer.role;
    card.querySelector(".toggle").setAttribute("aria-pressed", String(observer.enabled));
  });
  renderObservers();
}

function renderObservers() {
  let enabledCount = 0;
  elements.observerCards.forEach((card, index) => {
    const observer = state.observers[index];
    const model = modelFor(observer.provider, observer.model);
    if (observer.enabled) {
      enabledCount += 1;
    }
    card.classList.toggle("is-disabled", !observer.enabled);
    card.querySelector("[data-observer-role]").textContent = observer.role;
    card.querySelector("[data-observer-status]").textContent = observer.enabled ? observer.state : "disabled";
    card.querySelector("[data-observer-summary]").textContent = observer.enabled
      ? observer.summary
      : "Observer slot disabled in current in-memory display configuration.";
    card.querySelector("[data-observer-model]").textContent = observer.enabled
      ? `${providerLabel(observer.provider)} · ${model?.displayName || observer.model || "unconfigured"}`
      : "not observing";
  });
  elements.observerCount.textContent = `${enabledCount}/3 enabled`;
}

function renderConnections() {
  elements.connectionList.replaceChildren();
  const configured = state.routerStatus?.provider_configured || {};
  for (const providerId of providerIds()) {
    const providerModels = modelsFor(providerId);
    const hasDemoOnly = providerModels.every((model) => model.demoOnly);
    const isConfigured = Boolean(configured[providerId]) && !hasDemoOnly;
    const item = document.createElement("article");
    item.className = "connection-item";
    const identity = document.createElement("div");
    identity.className = "connection-identity";
    const mark = document.createElement("span");
    mark.className = "provider-icon";
    mark.textContent = providerMark(providerId);
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = providerLabel(providerId);
    const detail = document.createElement("small");
    detail.textContent = hasDemoOnly ? "in-memory demo candidate" : `${providerModels.length} visible model${providerModels.length === 1 ? "" : "s"}`;
    copy.append(title, detail);
    identity.append(mark, copy);
    const badge = document.createElement("span");
    badge.className = `connection-state ${isConfigured ? "ready" : "blocked"}`;
    badge.textContent = isConfigured ? "configured" : hasDemoOnly ? "inert" : "unavailable";
    item.append(identity, badge);
    elements.connectionList.append(item);
  }
}

function clearApiTransient() {
  elements.apiKey.value = "";
  elements.baseUrl.value = "";
  elements.providerConfirm.value = "";
  elements.detectedProvider.textContent = "Waiting for local candidate input";
  elements.detectionNote.textContent = "No network request is performed.";
  elements.detectionConfidence.textContent = "—";
}

function detectProviderCandidate({ key, baseUrl }) {
  const normalizedBase = String(baseUrl || "").trim().toLowerCase();
  const prefix = String(key || "").trim().slice(0, 12);
  if (normalizedBase.includes("openrouter")) {
    return { candidates: ["OpenRouter"], confidence: "high", explanation: "Base URL resembles the OpenRouter domain. User confirmation is still required." };
  }
  if (normalizedBase.includes("google") || normalizedBase.includes("generativelanguage")) {
    return { candidates: ["Google AI"], confidence: "high", explanation: "Base URL resembles a Google AI endpoint. User confirmation is still required." };
  }
  if (normalizedBase.includes("anthropic")) {
    return { candidates: ["Anthropic"], confidence: "high", explanation: "Base URL resembles an Anthropic endpoint. User confirmation is still required." };
  }
  if (normalizedBase) {
    return { candidates: ["Custom / OpenAI-compatible"], confidence: "medium", explanation: "A custom Base URL was entered; compatibility is not verified." };
  }
  if (prefix.startsWith("sk-ant-")) {
    return { candidates: ["Anthropic"], confidence: "medium", explanation: "The key prefix resembles Anthropic, but a prefix is not proof." };
  }
  if (prefix.startsWith("AIza")) {
    return { candidates: ["Google AI"], confidence: "medium", explanation: "The key prefix resembles Google AI, but a prefix is not proof." };
  }
  if (prefix.startsWith("sk-or-")) {
    return { candidates: ["OpenRouter"], confidence: "medium", explanation: "The key prefix resembles OpenRouter, but a prefix is not proof." };
  }
  if (prefix.startsWith("sk-")) {
    return { candidates: ["OpenAI", "xAI", "Mistral"], confidence: "low", explanation: "This prefix is shared by multiple providers. Explicit selection is required." };
  }
  if (prefix) {
    return { candidates: [], confidence: "unknown", explanation: "No reliable candidate can be inferred. Explicit selection is required." };
  }
  return { candidates: [], confidence: "—", explanation: "No network request is performed." };
}

function renderDetection() {
  const result = detectProviderCandidate({ key: elements.apiKey.value, baseUrl: elements.baseUrl.value });
  elements.detectedProvider.textContent = result.candidates.length
    ? `Candidate${result.candidates.length > 1 ? "s" : ""}: ${result.candidates.join(", ")}`
    : "No provider candidate detected";
  elements.detectionNote.textContent = result.explanation;
  elements.detectionConfidence.textContent = result.confidence;
}

function addDemoProviderCandidate(providerName) {
  const providerId = `demo_${providerName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`;
  if (!state.models.some((model) => model.providerId === providerId)) {
    state.models.push({
      providerId,
      modelId: `${providerId}/unverified-model`,
      displayName: "Unverified model candidate",
      source: "demo",
      demoOnly: true,
    });
  }
  hydratePrimarySelectors();
  hydrateObserverSelectors();
  renderConnections();
}

function appendMessage({ role, label, text, metadata = [], error = false }) {
  const row = document.createElement("article");
  row.className = `message-row ${role}${error ? " error" : ""}`;
  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "YOU" : error ? "!" : "AO";
  const content = document.createElement("div");
  content.className = "message-content";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const author = document.createElement("strong");
  author.textContent = label;
  meta.append(author);
  if (role !== "user") {
    const trust = document.createElement("span");
    trust.textContent = error ? "blocked" : "untrusted / non-authoritative";
    meta.append(trust);
  }
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  content.append(meta, bubble);
  if (metadata.length) {
    const evidence = document.createElement("div");
    evidence.className = "message-evidence";
    for (const item of metadata) {
      const chip = document.createElement("span");
      chip.textContent = item;
      evidence.append(chip);
    }
    content.append(evidence);
  }
  row.append(avatar, content);
  elements.chatHistory.append(row);
  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
  return row;
}

function appendTypingIndicator() {
  const row = appendMessage({ role: "system", label: "AOIA", text: "Requesting one controlled provider response…", metadata: ["no streaming", "no retry", "no fallback"] });
  row.dataset.typing = "true";
  return row;
}

function autoGrowComposer() {
  elements.chatInput.style.height = "0px";
  elements.chatInput.style.height = `${Math.min(elements.chatInput.scrollHeight, 148)}px`;
}

function setChatBusy(busy) {
  state.chatBusy = busy;
  updateConnectionState();
}

async function sendPrompt(prompt) {
  const selected = modelFor(state.selectedProvider, state.selectedModel);
  const configured = Boolean(state.routerStatus?.provider_configured?.[state.selectedProvider]);
  if (!isControlledChatModel(selected) || selected.demoOnly || !configured) {
    appendMessage({ role: "system", label: "AOIA blocked", text: "The selected route is unavailable for the existing controlled chat endpoint.", metadata: ["no provider call", "no fallback"], error: true });
    return;
  }

  setChatBusy(true);
  const typing = appendTypingIndicator();
  try {
    const result = await fetchJson("/api/operator/chat", {
      method: "POST",
      body: JSON.stringify({ provider_id: state.selectedProvider, model_id: state.selectedModel, prompt }),
    });
    typing.remove();
    appendMessage({
      role: "assistant",
      label: `${providerLabel(result.provider_id || state.selectedProvider)} · ${result.model_id || state.selectedModel}`,
      text: result.response_text || "Provider returned no text.",
      metadata: [
        `status: ${result.status || "unknown"}`,
        `trust: ${result.trust_status || "untrusted"}`,
        "authority: none",
      ],
    });
  } catch (error) {
    typing.remove();
    appendMessage({
      role: "system",
      label: "Controlled request blocked",
      text: error.message,
      metadata: ["no retry", "no fallback", "route unchanged"],
      error: true,
    });
  } finally {
    setChatBusy(false);
    elements.chatInput.focus();
  }
}

async function transformComposerPrompt() {
  const prompt = elements.chatInput.value.trim();
  if (!prompt || state.chatBusy) {
    elements.cptStatus.textContent = "Enter a draft first. Human review required. Manual send required.";
    return;
  }
  elements.criticTransform.disabled = true;
  elements.cptStatus.textContent = "Transforming locally. No provider send is allowed.";
  try {
    const payload = await fetchJson("/api/cpt/transform", {
      method: "POST",
      body: JSON.stringify({ prompt, mode: "balanced_critic" }),
    });
    const record = payload.record || {};
    elements.chatInput.value = String(record.transformed_prompt || prompt);
    autoGrowComposer();
    elements.cptStatus.textContent = `CPT ready · canonical_status: ${record.canonical_status || "non_canonical"}. Human review required. Manual send required.`;
    elements.chatInput.focus();
  } catch (error) {
    elements.cptStatus.textContent = `CPT blocked: ${error.message} Human review required. Manual send required.`;
  } finally {
    elements.criticTransform.disabled = state.chatBusy;
  }
}

async function previewSelectedRoute() {
  elements.previewRoute.disabled = true;
  elements.routerProposalResult.textContent = "Building inert route preview…";
  try {
    const payload = await fetchJson("/api/router/preview", {
      method: "POST",
      body: JSON.stringify({
        provider_id: state.selectedProvider,
        model_id: state.selectedModel,
        task_sensitivity: state.taskMode,
        user_prompt: elements.chatInput.value,
      }),
    });
    elements.routerProposalResult.textContent = [
      `status: ${payload.status}`,
      `request: ${shortHash(payload.request_hash)}`,
      `preview: ${shortHash(payload.preview_hash)}`,
      `provider call permitted: ${Boolean(payload.provider_call_permitted)}`,
      `human barrier connected: ${Boolean(payload.human_barrier_connected)}`,
    ].join("\n");
  } catch (error) {
    elements.routerProposalResult.textContent = `Preview blocked: ${error.message}`;
  } finally {
    elements.previewRoute.disabled = false;
  }
}

function renderEvidence(payload) {
  const evidence = payload?.evidence || {};
  elements.requestHash.textContent = shortHash(evidence.request_hash);
  elements.previewHash.textContent = shortHash(evidence.preview_hash);
  elements.governanceHash.textContent = shortHash(evidence.governance_hash);
  elements.barrierHash.textContent = shortHash(evidence.barrier_hash);
  elements.resultHash.textContent = shortHash(evidence.result_hash);
  elements.evidenceReasons.textContent = Array.isArray(evidence.reason_codes) ? evidence.reason_codes.join(" · ") : "missing";
}

function renderAudit(payload) {
  elements.auditMessages.replaceChildren();
  const messages = Array.isArray(payload?.messages) ? payload.messages : ["Audit endpoint unavailable. No authority inferred."];
  for (const message of messages) {
    const item = document.createElement("li");
    item.textContent = message;
    elements.auditMessages.append(item);
  }
}

function renderBoundaries(payload) {
  const boundaries = Array.isArray(payload?.boundaries) ? payload.boundaries : [];
  elements.boundaryCount.textContent = boundaries.length
    ? `${boundaries.length} existing boundaries · all displayed as read-only metadata.`
    : "Boundary endpoint unavailable. No authority inferred.";
  elements.boundaryList.replaceChildren();
  for (const boundary of boundaries) {
    const item = document.createElement("div");
    item.className = "boundary-item";
    const label = document.createElement("strong");
    label.textContent = boundary.label;
    const status = document.createElement("span");
    status.textContent = boundary.can_execute ? "unexpected executable state" : "inert · human review";
    item.append(label, status);
    elements.boundaryList.append(item);
  }
}

function renderCommits(payload) {
  const commits = Array.isArray(payload?.commits) ? payload.commits : [];
  elements.commitStatus.textContent = payload?.ok
    ? `${commits.length} local commits returned by the existing allowlisted read adapter.`
    : "Commit history unavailable. No Git write path is present.";
  elements.commitTableBody.replaceChildren();
  if (!commits.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = "No commit rows available.";
    row.append(cell);
    elements.commitTableBody.append(row);
    return;
  }
  for (const commit of commits) {
    const row = document.createElement("tr");
    for (const value of [commit.short_sha, commit.committed_at, commit.author, commit.subject]) {
      const cell = document.createElement("td");
      cell.textContent = String(value || "—");
      row.append(cell);
    }
    elements.commitTableBody.append(row);
  }
}

function openObserverDetail(index, opener) {
  const observer = state.observers[index];
  const model = modelFor(observer.provider, observer.model);
  elements.observerDetailNumber.textContent = String(index + 1).padStart(2, "0");
  elements.observerDetailTitle.textContent = `${observer.role} observer report`;
  elements.observerDetailRole.textContent = observer.role;
  elements.observerDetailModel.textContent = observer.enabled
    ? `${providerLabel(observer.provider)} · ${model?.displayName || observer.model || "unconfigured"}`
    : "disabled in current session";
  elements.observerFindingList.replaceChildren();
  const findings = [
    observer.enabled ? observer.summary : "This observer slot is disabled.",
    "The current backend exposes no observer execution/report endpoint, so no critic result is fabricated.",
    "Configuration is in-memory display metadata and does not call a provider or mutate a gate.",
    "The observer cannot approve, dispatch, write, execute, retry, or switch the primary route.",
  ];
  for (const finding of findings) {
    const item = document.createElement("article");
    const heading = document.createElement("strong");
    heading.textContent = "Read-only finding";
    const text = document.createElement("p");
    text.textContent = finding;
    item.append(heading, text);
    elements.observerFindingList.append(item);
  }
  openDialog(elements.observerDialog, opener, elements.observerDetailTitle);
}

async function loadReadOnlyCockpitData() {
  const entries = Object.entries(API_PATHS);
  const results = await Promise.allSettled(entries.map(([, path]) => fetchJson(path)));
  results.forEach((result, index) => {
    const [key] = entries[index];
    if (result.status === "fulfilled") {
      if (key === "operator") state.operatorStatus = result.value;
      if (key === "router") state.routerStatus = result.value;
      if (key === "evidence") state.evidence = result.value;
      if (key === "boundaries") state.boundaries = result.value;
      if (key === "loop") state.loopStatus = result.value;
      if (key === "audit") state.auditStatus = result.value;
      if (key === "commits") state.commits = result.value;
    }
  });

  const routerModels = Array.isArray(state.routerStatus?.models)
    ? state.routerStatus.models.map((model) => ({ ...model, source: "router-status" }))
    : [];
  state.models = mergeModels(
    OPERATOR_MODEL_OPTIONS.map((model) => ({ ...model, source: "operator-config" })),
    routerModels,
  );
  hydratePrimarySelectors();
  hydrateObserverSelectors();
  renderConnections();
  renderEvidence(state.evidence);
  renderAudit(state.auditStatus);
  renderBoundaries(state.boundaries);
  renderCommits(state.commits);
}

elements.settingsButton.addEventListener("click", () => openSettingsTo("connections", elements.settingsButton));
elements.primaryRouteButton.addEventListener("click", () => openSettingsTo("primary", elements.primaryRouteButton));
elements.auditButton.addEventListener("click", () => openDialog(elements.auditDialog, elements.auditButton, document.querySelector("#audit-title")));

for (const button of document.querySelectorAll("[data-close-dialog]")) {
  button.addEventListener("click", () => closeDialog(document.querySelector(`#${button.dataset.closeDialog}`)));
}

for (const dialog of [elements.settingsDialog, elements.auditDialog, elements.observerDialog]) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog(dialog);
  });
  dialog.addEventListener("close", () => {
    if (dialog === elements.settingsDialog) clearApiTransient();
    const opener = dialogOpeners.get(dialog);
    dialogOpeners.delete(dialog);
    if (opener instanceof HTMLElement && opener.isConnected) {
      window.requestAnimationFrame(() => opener.focus());
    }
  });
}

elements.tabButtons.forEach((button, index) => {
  button.addEventListener("click", () => activateSettingsTab(button.dataset.tab));
  button.addEventListener("keydown", (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % elements.tabButtons.length;
    if (event.key === "ArrowLeft") next = (index - 1 + elements.tabButtons.length) % elements.tabButtons.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = elements.tabButtons.length - 1;
    activateSettingsTab(elements.tabButtons[next].dataset.tab, true);
  });
});

elements.observerCards.forEach((card, index) => card.addEventListener("click", () => openObserverDetail(index, card)));

elements.routerProviderSelect.addEventListener("change", () => {
  state.selectedProvider = elements.routerProviderSelect.value;
  const availableModels = modelsFor(state.selectedProvider);
  state.selectedModel = availableModels[0]?.modelId || "";
  hydratePrimarySelectors();
});

elements.routerModelSelect.addEventListener("change", () => {
  state.selectedModel = elements.routerModelSelect.value;
  updateRouteReadout();
});

elements.routerTaskMode.addEventListener("change", () => {
  state.taskMode = elements.routerTaskMode.value;
});

elements.previewRoute.addEventListener("click", previewSelectedRoute);

elements.slotCards.forEach((card, index) => {
  const providerSelect = card.querySelector(".slot-provider");
  const modelSelect = card.querySelector(".slot-model");
  const roleSelect = card.querySelector(".slot-role");
  const toggle = card.querySelector(".toggle");
  providerSelect.addEventListener("change", () => {
    state.observers[index].provider = providerSelect.value;
    state.observers[index].model = modelsFor(providerSelect.value)[0]?.modelId || "";
    hydrateObserverSelectors();
  });
  modelSelect.addEventListener("change", () => {
    state.observers[index].model = modelSelect.value;
    renderObservers();
  });
  roleSelect.addEventListener("change", () => {
    state.observers[index].role = roleSelect.value;
    renderObservers();
  });
  toggle.addEventListener("click", () => {
    state.observers[index].enabled = !state.observers[index].enabled;
    toggle.setAttribute("aria-pressed", String(state.observers[index].enabled));
    renderObservers();
  });
});

elements.applyLoop.addEventListener("click", () => showToast("Observer display configuration applied in memory only. No critic was called.", "neutral"));

elements.showApiForm.addEventListener("click", () => {
  elements.apiForm.classList.add("is-open");
  elements.apiKey.focus();
});
elements.apiKey.addEventListener("input", renderDetection);
elements.baseUrl.addEventListener("input", renderDetection);

elements.cancelApi.addEventListener("click", () => {
  clearApiTransient();
  elements.apiForm.classList.remove("is-open");
  elements.apiFlowStatus.textContent = "Cancelled. Temporary fields cleared; no request was made.";
  elements.showApiForm.focus();
});

elements.apiForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const hasKey = Boolean(elements.apiKey.value.trim());
  const confirmedProvider = elements.providerConfirm.value;
  const customNeedsUrl = confirmedProvider === "Custom / OpenAI-compatible" && !elements.baseUrl.value.trim();
  if (!hasKey || !confirmedProvider || customNeedsUrl) {
    elements.apiFlowStatus.textContent = customNeedsUrl
      ? "Blocked: a custom provider requires a Base URL and explicit confirmation."
      : "Blocked: enter a candidate key and explicitly confirm the provider.";
    clearApiTransient();
    return;
  }
  try {
    addDemoProviderCandidate(confirmedProvider);
    elements.apiFlowStatus.textContent = `${confirmedProvider} added to the in-memory UI catalog as unverified and inert. No provider request was made.`;
    showToast("Inert provider candidate added to this UI session only.", "neutral");
  } finally {
    clearApiTransient();
    elements.apiForm.classList.remove("is-open");
  }
});

elements.chatInput.addEventListener("input", autoGrowComposer);
elements.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
});

elements.chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = elements.chatInput.value.trim();
  if (!prompt || state.chatBusy) return;
  appendMessage({ role: "user", label: "You", text: prompt, metadata: [`route: ${providerLabel(state.selectedProvider)} · ${state.selectedModel}`, "manual send"] });
  elements.chatInput.value = "";
  autoGrowComposer();
  void sendPrompt(prompt);
});

elements.criticTransform.addEventListener("click", transformComposerPrompt);

state.models = mergeModels(OPERATOR_MODEL_OPTIONS.map((model) => ({ ...model, source: "operator-config" })));
hydratePrimarySelectors();
hydrateObserverSelectors();
renderConnections();
updateConnectionState();
autoGrowComposer();
void loadReadOnlyCockpitData();
