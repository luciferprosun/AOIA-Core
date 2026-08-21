import { OPERATOR_MODEL_OPTIONS } from "./operator_config.js";

const state = {
  routerStatus: null,
  models: [],
  selectedProvider: "",
  selectedModel: "",
  selectedMode: "PUBLIC_DEV",
  operatorToken: "",
  running: false,
};

const PROVIDER_LABELS = {
  disabled: "Disabled",
  gemini: "Gemini",
  gemini_chat: "Gemini",
  kimi: "Kimi",
  kimi_chat: "Kimi",
  local: "Local",
  openrouter: "OpenRouter",
  openrouter_chat: "OpenRouter",
};

const MODE_LABELS = {
  PUBLIC_DEV: "Chat / public dev",
  SENSITIVE: "Safe Review",
  CANONICAL: "Audit / canonical",
  SECRET_ADJACENT: "Secret-adjacent",
};

const elements = {
  navItems: document.querySelectorAll(".nav-item"),
  views: document.querySelectorAll(".view"),
  operatorToken: document.querySelector("#operator-token"),
  refreshAll: document.querySelector("#refresh-all"),
  topBot: document.querySelector("#top-bot"),
  topMode: document.querySelector("#top-mode"),
  topModel: document.querySelector("#top-model"),
  runStatus: document.querySelector("#run-status"),
  connectionStatus: document.querySelector("#connection-status"),
  safetyMode: document.querySelector("#safety-mode"),
  chatState: document.querySelector("#chat-state"),
  chatHistory: document.querySelector("#chat-history"),
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  sendChat: document.querySelector("#send-chat"),
  newChat: document.querySelector("#new-chat"),
  stopChat: document.querySelector("#stop-chat"),
  chatProvider: document.querySelector("#chat-provider"),
  chatModel: document.querySelector("#chat-model"),
  chatMode: document.querySelector("#chat-mode"),
  chatCallable: document.querySelector("#chat-callable"),
  chatDisabledReason: document.querySelector("#chat-disabled-reason"),
  dashboardState: document.querySelector("#dashboard-state"),
  gitBranch: document.querySelector("#git-branch"),
  gitHead: document.querySelector("#git-head"),
  gitClean: document.querySelector("#git-clean"),
  gitReasons: document.querySelector("#git-reasons"),
  roadmapBlock: document.querySelector("#roadmap-block"),
  freezeStatus: document.querySelector("#freeze-status"),
  operatorSafetyMode: document.querySelector("#operator-safety-mode"),
  routerProviderSelect: document.querySelector("#router-provider-select"),
  routerModelSelect: document.querySelector("#router-model-select"),
  routerTaskMode: document.querySelector("#router-task-mode"),
  routerState: document.querySelector("#router-state"),
  routerPreview: document.querySelector("#router-preview"),
  providerConfigured: document.querySelector("#provider-configured"),
  connectionCallable: document.querySelector("#connection-callable"),
  humanBarrier: document.querySelector("#human-barrier"),
  disabledReason: document.querySelector("#disabled-reason"),
  safeNextStep: document.querySelector("#safe-next-step"),
  providerCallButton: document.querySelector("#provider-call-button"),
  composer: document.querySelector("#composer"),
  promptInput: document.querySelector("#prompt-input"),
  criticTransform: document.querySelector("#critic-transform"),
  cptStatus: document.querySelector("#cpt-status"),
  routerProposalResult: document.querySelector("#router-proposal-result"),
  requestHash: document.querySelector("#request-hash"),
  previewHash: document.querySelector("#preview-hash"),
  governanceHash: document.querySelector("#governance-hash"),
  barrierHash: document.querySelector("#barrier-hash"),
  resultHash: document.querySelector("#result-hash"),
  evidenceState: document.querySelector("#evidence-state"),
  evidenceReasons: document.querySelector("#evidence-reasons"),
  boundaryCount: document.querySelector("#boundary-count"),
  boundaryList: document.querySelector("#boundary-list"),
  localObjective: document.querySelector("#local-objective"),
  localSelected: document.querySelector("#local-selected"),
  localRisk: document.querySelector("#local-risk"),
  localReasons: document.querySelector("#local-reasons"),
  providerObjective: document.querySelector("#provider-objective"),
  providerSelected: document.querySelector("#provider-selected"),
  providerRisk: document.querySelector("#provider-risk"),
  providerReasons: document.querySelector("#provider-reasons"),
  auditMessages: document.querySelector("#audit-messages"),
  commitCount: document.querySelector("#commit-count"),
  commitStatus: document.querySelector("#commit-status"),
  commitTableBody: document.querySelector("#commit-table-body"),
  providerConfigStatus: document.querySelector("#provider-config-status"),
  selectedProvider: document.querySelector("#selected-provider"),
  selectedModel: document.querySelector("#selected-model"),
  selectedMode: document.querySelector("#selected-mode"),
};

async function jsonFetch(url, options = {}) {
  if (!state.operatorToken) {
    throw new Error("Local operator token required.");
  }
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${state.operatorToken}`,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(url, {
    ...options,
    headers,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message_safe || payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function setConnectionStatus(label, tone = "ok") {
  elements.connectionStatus.textContent = label;
  elements.connectionStatus.className = `status-dot status-${tone}`;
}

function shortHash(value) {
  if (!value || value === "missing") {
    return "missing";
  }
  return String(value);
}

function providerLabel(providerId) {
  return PROVIDER_LABELS[providerId] || providerId || "Unknown";
}

function modeLabel(mode) {
  return MODE_LABELS[mode] || mode || "Chat / public dev";
}

function boolText(value, trueText = "Yes", falseText = "No") {
  return value ? trueText : falseText;
}

function joinCodes(codes) {
  if (!codes || codes.length === 0) {
    return "-";
  }
  return Array.from(codes).join(", ");
}

function uniqueModels(models) {
  const byKey = new Map();
  for (const model of [...(models || []), ...OPERATOR_MODEL_OPTIONS]) {
    byKey.set(`${model.provider_id}:${model.model_id}`, model);
  }
  return [...byKey.values()].sort((a, b) => {
    const providerOrder = providerLabel(a.provider_id).localeCompare(providerLabel(b.provider_id));
    if (providerOrder !== 0) {
      return providerOrder;
    }
    return (a.display_name || a.model_id).localeCompare(b.display_name || b.model_id);
  });
}

function showView(targetId) {
  for (const item of elements.navItems) {
    item.classList.toggle("active", item.dataset.target === targetId);
  }
  for (const view of elements.views) {
    view.classList.toggle("active-view", view.id === targetId);
  }
}

function renderOperatorStatus(payload) {
  const git = payload.git || {};
  elements.dashboardState.textContent = payload.ok ? "ready" : "blocked";
  elements.gitBranch.textContent = git.branch || "-";
  elements.gitHead.textContent = git.head || "-";
  elements.gitClean.textContent = git.clean === true ? "clean" : "dirty or unavailable";
  elements.gitReasons.textContent = joinCodes(git.reason_codes);
  elements.roadmapBlock.textContent = payload.roadmap_block || "Steps 42-54 complete";
  elements.freezeStatus.textContent = payload.prototype_freeze_status || "unknown";
  elements.operatorSafetyMode.textContent = payload.safety_mode || "preview-only";
  elements.safetyMode.textContent = payload.safety_mode || "Preview-only";
}

function hydrateRouterControls(payload) {
  state.routerStatus = payload;
  state.models = uniqueModels(payload.models || []);
  const providerIds = [...new Set(state.models.map((model) => model.provider_id))];

  elements.routerProviderSelect.innerHTML = "";
  for (const providerId of providerIds) {
    const option = document.createElement("option");
    option.value = providerId;
    option.textContent = providerLabel(providerId);
    elements.routerProviderSelect.appendChild(option);
  }
  state.selectedProvider = state.selectedProvider || providerIds[0] || "disabled";
  elements.routerProviderSelect.value = state.selectedProvider;
  hydrateModelSelect();
  renderRouterStatus(payload);
}

function hydrateModelSelect() {
  const providerId = elements.routerProviderSelect.value;
  const models = state.models.filter((model) => model.provider_id === providerId);
  elements.routerModelSelect.innerHTML = "";
  for (const model of models) {
    const option = document.createElement("option");
    option.value = model.model_id;
    option.textContent = model.display_name ? `${model.display_name} (${model.model_id})` : model.model_id;
    elements.routerModelSelect.appendChild(option);
  }
  state.selectedProvider = providerId;
  state.selectedModel = models.some((model) => model.model_id === state.selectedModel)
    ? state.selectedModel
    : models[0]?.model_id || "";
  elements.routerModelSelect.value = state.selectedModel;
  syncSelectionReadout();
  renderRouterStatus(state.routerStatus || {});
}

function syncSelectionReadout() {
  state.selectedProvider = elements.routerProviderSelect.value;
  state.selectedModel = elements.routerModelSelect.value;
  state.selectedMode = elements.routerTaskMode.value;
  elements.selectedProvider.textContent = providerLabel(state.selectedProvider);
  elements.selectedModel.textContent = state.selectedModel || "-";
  elements.selectedMode.textContent = modeLabel(state.selectedMode);
  elements.topBot.textContent = "Default";
  elements.topMode.textContent = modeLabel(state.selectedMode);
  elements.topModel.textContent = state.selectedModel || "-";
  elements.chatProvider.textContent = providerLabel(state.selectedProvider);
  elements.chatModel.textContent = state.selectedModel || "-";
  elements.chatMode.textContent = modeLabel(state.selectedMode);
}

function renderRouterStatus(payload) {
  const configured = payload.provider_configured || {};
  const providerConfigured = configured[elements.routerProviderSelect.value] === true;
  elements.routerState.textContent = payload.status || "preview_only";
  elements.providerConfigured.textContent = boolText(providerConfigured, "Configured", "Not configured");
  elements.connectionCallable.textContent = boolText(payload.connection_callable, "Callable", "No");
  elements.chatCallable.textContent = boolText(payload.connection_callable, "Callable", "No");
  elements.humanBarrier.textContent = payload.human_barrier_connected ? "Connected" : "Not connected";
  elements.disabledReason.textContent =
    payload.reason || "Preview only - no controlled execution path connected.";
  elements.chatDisabledReason.textContent =
    payload.notice || payload.reason || "Provider call disabled in this build.";
  elements.safeNextStep.textContent =
    payload.safe_next_step || "Review inert preview evidence; do not execute provider calls from this UI.";
  elements.providerCallButton.disabled = true;
  elements.providerCallButton.textContent = "Use Chat Send";
  elements.providerConfigStatus.textContent = [
    `Kimi: ${configured.kimi_chat || configured.kimi ? "configured" : "not configured"}`,
    `Gemini: ${configured.gemini ? "configured" : "not configured"}`,
    `OpenRouter: ${configured.openrouter ? "configured" : "not configured"}`,
  ].join(" / ");
}

function renderEvidence(payload) {
  const evidence = payload.evidence || {};
  elements.evidenceState.textContent = evidence.status || "missing";
  elements.requestHash.textContent = shortHash(evidence.request_hash);
  elements.previewHash.textContent = shortHash(evidence.preview_hash);
  elements.governanceHash.textContent = shortHash(evidence.governance_hash);
  elements.barrierHash.textContent = shortHash(evidence.barrier_hash);
  elements.resultHash.textContent = shortHash(evidence.result_hash);
  elements.evidenceReasons.textContent = joinCodes(evidence.reason_codes);
}

function renderBoundaryMap(payload) {
  const boundaries = payload.boundaries || [];
  elements.boundaryCount.textContent = `${boundaries.length} boundaries`;
  elements.boundaryList.innerHTML = "";
  for (const boundary of boundaries) {
    const card = document.createElement("article");
    card.className = "boundary-card";
    const title = document.createElement("h4");
    title.textContent = boundary.label;
    const facts = document.createElement("dl");
    facts.className = "mini-facts";
    facts.innerHTML = `
      <div><dt>Status</dt><dd>${boundary.status}</dd></div>
      <div><dt>Metadata</dt><dd>${boolText(boundary.inert_metadata, "Inert", "Unknown")}</dd></div>
      <div><dt>Can execute</dt><dd>${boolText(boundary.can_execute)}</dd></div>
      <div><dt>Human review</dt><dd>${boolText(boundary.requires_human_review, "Required", "No")}</dd></div>
    `;
    const reason = document.createElement("p");
    reason.className = "reason-line";
    reason.textContent = joinCodes(boundary.reason_codes);
    card.append(title, facts, reason);
    elements.boundaryList.appendChild(card);
  }
}

function renderAgentLoop(payload) {
  const local = payload.local_loop || {};
  const provider = payload.provider_loop || {};
  elements.localObjective.textContent = local.objective_summary || "-";
  elements.localSelected.textContent = local.selected_candidate || "None";
  elements.localRisk.textContent = local.risk_tier || "-";
  elements.localReasons.textContent = joinCodes(local.reason_codes);
  elements.providerObjective.textContent = provider.objective_summary || "-";
  elements.providerSelected.textContent = provider.selected_candidate || "None";
  elements.providerRisk.textContent = provider.risk_tier || "-";
  elements.providerReasons.textContent = joinCodes(provider.reason_codes);
}

function renderAudit(payload) {
  elements.auditMessages.innerHTML = "";
  for (const message of payload.messages || []) {
    const item = document.createElement("li");
    item.textContent = message;
    elements.auditMessages.appendChild(item);
  }
}

function renderCommitHistory(payload) {
  const commits = payload.commits || [];
  elements.commitCount.textContent = payload.ok ? `${commits.length} commits` : "blocked";
  elements.commitStatus.textContent = payload.ok
    ? "All local commits returned by the read-only Git adapter."
    : `Commit history blocked: ${payload.reason_code || "unknown reason"}`;
  elements.commitTableBody.innerHTML = "";

  if (!payload.ok || commits.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = payload.ok ? "No commits found." : "Commit history is unavailable.";
    row.appendChild(cell);
    elements.commitTableBody.appendChild(row);
    return;
  }

  for (const commit of commits) {
    const row = document.createElement("tr");

    const sha = document.createElement("td");
    sha.className = "commit-sha";
    sha.textContent = commit.short_sha || "";
    sha.title = commit.sha || "";

    const committedAt = document.createElement("td");
    committedAt.textContent = commit.committed_at || "";

    const author = document.createElement("td");
    author.textContent = commit.author || "";

    const subject = document.createElement("td");
    subject.textContent = commit.subject || "";

    row.append(sha, committedAt, author, subject);
    elements.commitTableBody.appendChild(row);
  }
}

function renderJson(element, payload) {
  element.textContent = JSON.stringify(payload, null, 2);
}

function appendMessage(role, text, details = []) {
  const message = document.createElement("article");
  message.className = `message message-${role}`;
  const roleLabel = document.createElement("p");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? "You" : role === "assistant" ? "AOIA" : "System";
  const body = document.createElement("p");
  body.textContent = text;
  message.append(roleLabel, body);

  if (details.length > 0) {
    const list = document.createElement("ul");
    list.className = "message-details";
    for (const detail of details) {
      const item = document.createElement("li");
      item.textContent = detail;
      list.appendChild(item);
    }
    message.appendChild(list);
  }

  elements.chatHistory.appendChild(message);
  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

function resetChat() {
  elements.chatHistory.innerHTML = "";
  appendMessage(
    "system",
    "New local chat started. Messages create preview metadata only; no provider request is sent.",
  );
  elements.chatState.textContent = "Preview only";
}

async function previewRouterSelection() {
  syncSelectionReadout();
  const payload = await jsonFetch("/api/router/preview", {
    method: "POST",
    body: JSON.stringify({
      provider_id: state.selectedProvider,
      model_id: state.selectedModel,
      task_sensitivity: state.selectedMode,
      user_prompt: elements.promptInput.value,
    }),
  });
  renderJson(elements.routerProposalResult, payload);
  elements.disabledReason.textContent = payload.disabled_reason || "Blocked: preview only.";
  elements.safeNextStep.textContent = payload.safe_next_step || "Review inert preview evidence only.";
  elements.requestHash.textContent = payload.request_hash || "missing";
  elements.previewHash.textContent = payload.preview_hash || "missing";
  elements.governanceHash.textContent = payload.decision_hash || "missing";
  elements.barrierHash.textContent = "missing";
  elements.resultHash.textContent = "missing";
  elements.evidenceState.textContent = "preview";
  elements.evidenceReasons.textContent = joinCodes(payload.reason_codes);
  showView("evidence");
  return payload;
}

async function previewChatMessage() {
  const prompt = elements.chatInput.value.trim();
  if (!prompt || state.running) {
    return;
  }

  syncSelectionReadout();
  state.running = true;
  elements.runStatus.textContent = "Previewing";
  elements.chatState.textContent = "Previewing";
  elements.sendChat.disabled = true;
  appendMessage("user", prompt);
  elements.chatInput.value = "";

  try {
    const payload = await callOperatorChat(prompt);
    appendMessage("assistant", payload.response_text || "Provider returned no text.", [
      `Status: ${payload.status || "unknown"}`,
      `Model: ${state.selectedModel || "-"}`,
      `Provider call made: ${payload.call_made ? "yes" : "no"}`,
      `Trust: ${payload.trust_status || "UNTRUSTED"}`,
      `Authority: output is not authority`,
    ]);
    showView("chat");
    elements.chatState.textContent = "Idle";
  } catch (error) {
    appendMessage("assistant", "The provider call was blocked or failed before a trusted result was created.", [
      `Reason: ${String(error)}`,
    ]);
    elements.chatState.textContent = "Blocked";
  } finally {
    state.running = false;
    elements.runStatus.textContent = "Idle";
    elements.sendChat.disabled = false;
  }
}

async function callOperatorChat(prompt) {
  const payload = await jsonFetch("/api/operator/chat", {
    method: "POST",
    body: JSON.stringify({
      provider_id: state.selectedProvider || "kimi_chat",
      model_id: state.selectedModel || "moonshot-v1-8k",
      prompt,
    }),
  });
  elements.promptInput.value = prompt;
  renderJson(elements.routerProposalResult, payload);
  elements.evidenceState.textContent = payload.ok ? "live_untrusted" : "blocked";
  elements.requestHash.textContent = "provider-runtime-live";
  elements.previewHash.textContent = payload.status || "missing";
  elements.governanceHash.textContent = "manual-provider-runtime-1a";
  elements.barrierHash.textContent = "manual-send";
  elements.resultHash.textContent = payload.trust_status || "UNTRUSTED";
  elements.evidenceReasons.textContent = payload.ok
    ? "AOIA_PROVIDER_OUTPUT_UNTRUSTED"
    : payload.error || "AOIA_PROVIDER_CALL_BLOCKED";
  return payload;
}

async function sendPrompt(prompt) {
  state.running = true;
  const payload = await jsonFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
  state.running = false;
  return payload;
}

async function transformComposerPrompt() {
  const prompt = elements.promptInput.value;
  if (!prompt.trim()) {
    elements.cptStatus.textContent = "Enter a prompt before applying the transform.";
    return;
  }

  elements.criticTransform.disabled = true;
  elements.cptStatus.textContent = "Transform running locally. Manual send required.";
  try {
    const payload = await jsonFetch("/api/cpt/transform", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        mode: "balanced_critic",
      }),
    });
    elements.promptInput.value = payload.record.transformed_prompt;
    elements.promptInput.focus();
    elements.cptStatus.textContent = [
      "Transform applied.",
      payload.record.canonical_status,
      "Human review required.",
      "Manual send required.",
    ].join(" ");
  } catch (error) {
    elements.cptStatus.textContent = String(error);
  } finally {
    elements.criticTransform.disabled = false;
  }
}

async function refreshAll() {
  setConnectionStatus("loading", "warn");
  const [status, router, evidence, boundaries, agentLoop, audit, commits] = await Promise.all([
    jsonFetch("/api/operator/status"),
    jsonFetch("/api/router/status"),
    jsonFetch("/api/evidence/sample"),
    jsonFetch("/api/boundaries"),
    jsonFetch("/api/agent-loop/status"),
    jsonFetch("/api/audit/status"),
    jsonFetch("/api/commits"),
  ]);

  renderOperatorStatus(status);
  hydrateRouterControls(router);
  renderEvidence(evidence);
  renderBoundaryMap(boundaries);
  renderAgentLoop(agentLoop);
  renderAudit(audit);
  renderCommitHistory(commits);
  syncSelectionReadout();
  setConnectionStatus("connected", "ok");
}

for (const item of elements.navItems) {
  item.addEventListener("click", () => showView(item.dataset.target));
}

elements.refreshAll.addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    setConnectionStatus("error", "error");
    elements.disabledReason.textContent = String(error);
  }
});

elements.operatorToken.addEventListener("input", () => {
  state.operatorToken = elements.operatorToken.value;
  setConnectionStatus(state.operatorToken ? "token ready" : "token required", "warn");
});

elements.routerProviderSelect.addEventListener("change", hydrateModelSelect);
elements.routerModelSelect.addEventListener("change", syncSelectionReadout);
elements.routerTaskMode.addEventListener("change", syncSelectionReadout);
elements.routerPreview.addEventListener("click", async () => {
  try {
    await previewRouterSelection();
  } catch (error) {
    elements.disabledReason.textContent = `Blocked: ${error}`;
    renderJson(elements.routerProposalResult, { ok: false, error: String(error), call_made: false });
  }
});
elements.providerCallButton.addEventListener("click", () => {
  elements.disabledReason.textContent = "Use the Chat Send button for one controlled manual provider call.";
});
elements.criticTransform.addEventListener("click", async () => {
  await transformComposerPrompt();
});
elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await previewChatMessage();
});
elements.newChat.addEventListener("click", resetChat);
elements.stopChat.addEventListener("click", () => {
  elements.chatState.textContent = "No live provider call to stop";
});

elements.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = elements.promptInput.value.trim();
  if (!prompt || state.running) {
    return;
  }
  await sendPrompt(prompt);
});

refreshAll().catch((error) => {
  setConnectionStatus("error", "error");
  elements.disabledReason.textContent = String(error);
});
