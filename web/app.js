import { OPERATOR_MODEL_OPTIONS } from "./operator_config.js";

const state = {
  routerStatus: null,
  models: [],
  providerConnections: [],
  modelProfiles: [],
  orchestraModels: [],
  orchestraPreview: null,
  orchestraPreviewHash: "",
  selectedProvider: "",
  selectedModel: "",
  selectedMode: "PUBLIC_DEV",
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

const ORCHESTRA_ROLES = ["MAIN", "CRITIC", "AUDITOR", "SYNTHESIZER"];
const SENSITIVE_UI_FIELD_PARTS = ["api_key", "apikey", "authorization", "bearer", "password", "secret"];

const elements = {
  navItems: document.querySelectorAll(".nav-item"),
  views: document.querySelectorAll(".view"),
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
  providerConnectionForm: document.querySelector("#provider-connection-form"),
  providerConnectionId: document.querySelector("#provider-connection-id"),
  providerConnectionName: document.querySelector("#provider-connection-name"),
  providerApiStyle: document.querySelector("#provider-api-style"),
  providerBaseUrl: document.querySelector("#provider-base-url"),
  providerApiKey: document.querySelector("#provider-api-key"),
  providerConnectionFormStatus: document.querySelector("#provider-connection-form-status"),
  modelProfileForm: document.querySelector("#model-profile-form"),
  modelProfileId: document.querySelector("#model-profile-id"),
  modelProfileConnection: document.querySelector("#model-profile-connection"),
  modelProfileName: document.querySelector("#model-profile-name"),
  modelRemoteId: document.querySelector("#model-remote-id"),
  modelAllowedRoles: document.querySelector("#model-allowed-roles"),
  modelProfileFormStatus: document.querySelector("#model-profile-form-status"),
  orchestraPresetExamples: document.querySelector("#orchestra-preset-examples"),
  orchestraModelTableBody: document.querySelector("#orchestra-model-table-body"),
  orchestraSelectionCount: document.querySelector("#orchestra-selection-count"),
  refreshOrchestraModels: document.querySelector("#refresh-orchestra-models"),
  orchestraPrompt: document.querySelector("#orchestra-prompt"),
  previewOrchestraPlan: document.querySelector("#preview-orchestra-plan"),
  orchestraPreviewHash: document.querySelector("#orchestra-preview-hash"),
  orchestraConfirmationHash: document.querySelector("#orchestra-confirmation-hash"),
  orchestraConfirmPreview: document.querySelector("#orchestra-confirm-preview"),
  runOrchestra: document.querySelector("#run-orchestra"),
  orchestraLiveStatus: document.querySelector("#orchestra-live-status"),
  orchestraLiveResult: document.querySelector("#orchestra-live-result"),
};

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
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

function collectionFromPayload(payload, ...keys) {
  if (Array.isArray(payload)) {
    return payload;
  }
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }
  return [];
}

function boundedStatus(value, fallback = "unknown") {
  if (typeof value === "string") {
    return value.substring(0, 160) || fallback;
  }
  if (value && typeof value === "object") {
    const status = value.status || value.result || value.state;
    const testedAt = value.tested_at || value.created_at || value.timestamp;
    return [status, testedAt].filter(Boolean).join(" @ ").substring(0, 160) || fallback;
  }
  return fallback;
}

function safeUiPayload(value) {
  if (Array.isArray(value)) {
    return value.map((item) => safeUiPayload(item));
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  const safe = {};
  for (const [key, item] of Object.entries(value)) {
    const normalized = key.toLowerCase();
    if (SENSITIVE_UI_FIELD_PARTS.some((part) => normalized.includes(part))) {
      safe[key] = "[REDACTED]";
    } else {
      safe[key] = safeUiPayload(item);
    }
  }
  return safe;
}

function redactedError(error, knownSecret = "") {
  const message = String(error);
  return knownSecret ? message.split(knownSecret).join("[REDACTED]") : message;
}

function renderPresetExamples() {
  elements.orchestraPresetExamples.innerHTML = "";
  for (const model of OPERATOR_MODEL_OPTIONS) {
    const item = document.createElement("li");
    item.textContent = `${model.display_name || model.model_id} — optional example only`;
    elements.orchestraPresetExamples.appendChild(item);
  }
}

function connectionId(connection) {
  return String(connection.connection_id || connection.provider_id || "").trim();
}

function modelProfileId(model) {
  return String(model.model_profile_id || model.profile_id || "").trim();
}

function modelConnectionId(model) {
  return String(model.connection_id || model.provider_id || "").trim();
}

function connectionById(value) {
  return state.providerConnections.find((connection) => connectionId(connection) === value) || null;
}

function modelAllowedRoles(model) {
  const roles = Array.isArray(model.allowed_roles) ? model.allowed_roles : [];
  return roles.filter((role) => ORCHESTRA_ROLES.includes(role));
}

function modelIsSelectable(model, connection) {
  if (typeof model.selectable === "boolean") {
    return model.selectable;
  }
  if (model.enabled === false || connection?.enabled === false) {
    return false;
  }
  const statusText = [
    model.model_status,
    model.connection_status,
    connection?.status,
    connection?.credential_status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return !/(disabled|missing|unconfigured|blocked|invalid|error)/.test(statusText);
}

function populateModelConnectionSelect() {
  const previous = elements.modelProfileConnection.value;
  elements.modelProfileConnection.innerHTML = "";
  for (const connection of state.providerConnections) {
    const id = connectionId(connection);
    if (!id) {
      continue;
    }
    const option = document.createElement("option");
    option.value = id;
    option.textContent = connection.display_name || id;
    elements.modelProfileConnection.appendChild(option);
  }
  if ([...elements.modelProfileConnection.options].some((option) => option.value === previous)) {
    elements.modelProfileConnection.value = previous;
  }
}

function currentOrchestraUiState() {
  const selected = new Map();
  for (const checkbox of document.querySelectorAll(".orchestra-model-selected")) {
    const role = document.querySelector(`.orchestra-role-select[data-model-profile-id="${CSS.escape(checkbox.dataset.modelProfileId)}"]`);
    selected.set(checkbox.dataset.modelProfileId, {
      checked: checkbox.checked,
      role: role?.value || "",
    });
  }
  return selected;
}

function actionButton(label, className, handler, disabled = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.disabled = disabled;
  button.addEventListener("click", handler);
  return button;
}

function renderOrchestraModels() {
  const previous = currentOrchestraUiState();
  elements.orchestraModelTableBody.innerHTML = "";

  if (state.orchestraModels.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.textContent = "No saved model profiles. Add a connection and model above.";
    row.appendChild(cell);
    elements.orchestraModelTableBody.appendChild(row);
    updateOrchestraSelectionState();
    return;
  }

  for (const model of state.orchestraModels) {
    const profileId = modelProfileId(model);
    const linkedConnection = connectionById(modelConnectionId(model));
    const selectable = modelIsSelectable(model, linkedConnection);
    const remembered = previous.get(profileId);
    const row = document.createElement("tr");
    row.dataset.modelProfileId = profileId;

    const selectedCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "orchestra-model-selected";
    checkbox.dataset.modelProfileId = profileId;
    checkbox.checked = selectable && Boolean(remembered?.checked || model.selected);
    checkbox.disabled = !selectable;
    checkbox.setAttribute("aria-label", `Select ${model.display_name || profileId}`);
    selectedCell.appendChild(checkbox);

    const modelNameCell = document.createElement("td");
    modelNameCell.textContent = model.display_name || profileId;

    const connectionNameCell = document.createElement("td");
    connectionNameCell.textContent =
      model.connection_name || linkedConnection?.display_name || modelConnectionId(model) || "unknown";

    const remoteIdCell = document.createElement("td");
    remoteIdCell.textContent = model.remote_model_id || model.model_id || "unknown";

    const connectionStatusCell = document.createElement("td");
    const connectionStatus = boundedStatus(
      model.connection_status || linkedConnection?.credential_status || linkedConnection?.status,
      linkedConnection?.enabled === false ? "disabled" : "unknown",
    );
    const connectionStatusText = document.createElement("span");
    connectionStatusText.textContent = connectionStatus;
    connectionStatusCell.append(connectionStatusText);
    if (modelConnectionId(model)) {
      connectionStatusCell.append(
        document.createElement("br"),
        actionButton("Disable connection", "button button-subtle", () => disableConnection(modelConnectionId(model))),
      );
    }

    const modelStatusCell = document.createElement("td");
    const modelStatusText = document.createElement("span");
    modelStatusText.textContent = boundedStatus(model.model_status, model.enabled === false ? "disabled" : "enabled");
    modelStatusCell.append(modelStatusText);
    if (profileId) {
      modelStatusCell.append(
        document.createElement("br"),
        actionButton("Disable model", "button button-subtle", () => disableModelProfile(profileId)),
      );
    }

    const roleCell = document.createElement("td");
    const roleSelect = document.createElement("select");
    roleSelect.className = "select orchestra-role-select";
    roleSelect.dataset.modelProfileId = profileId;
    roleSelect.setAttribute("aria-label", `Assigned role for ${model.display_name || profileId}`);
    const emptyRole = document.createElement("option");
    emptyRole.value = "";
    emptyRole.textContent = "Choose role";
    roleSelect.appendChild(emptyRole);
    for (const role of modelAllowedRoles(model)) {
      const option = document.createElement("option");
      option.value = role;
      option.textContent = role;
      roleSelect.appendChild(option);
    }
    const requestedRole = remembered?.role || model.assigned_role || "";
    roleSelect.value = modelAllowedRoles(model).includes(requestedRole) ? requestedRole : "";
    roleSelect.disabled = !checkbox.checked;
    roleCell.appendChild(roleSelect);

    const testCell = document.createElement("td");
    const lastTest = document.createElement("span");
    lastTest.textContent = boundedStatus(model.last_connection_test, "not tested");
    testCell.append(
      lastTest,
      document.createElement("br"),
      actionButton("Test connection", "button button-subtle", () => testConnection(model), !selectable),
    );

    checkbox.addEventListener("change", () => {
      roleSelect.disabled = !checkbox.checked;
      if (!checkbox.checked) {
        roleSelect.value = "";
      }
      invalidateOrchestraPreview("Selection changed; generate a new preview.");
      updateOrchestraSelectionState();
    });
    roleSelect.addEventListener("change", () => {
      invalidateOrchestraPreview("Role assignment changed; generate a new preview.");
      updateOrchestraSelectionState();
    });

    row.append(
      selectedCell,
      modelNameCell,
      connectionNameCell,
      remoteIdCell,
      connectionStatusCell,
      modelStatusCell,
      roleCell,
      testCell,
    );
    elements.orchestraModelTableBody.appendChild(row);
  }
  updateOrchestraSelectionState();
}

function selectedOrchestraModels() {
  const selections = [];
  for (const checkbox of document.querySelectorAll(".orchestra-model-selected:checked")) {
    const profileId = checkbox.dataset.modelProfileId;
    const role = document.querySelector(`.orchestra-role-select[data-model-profile-id="${CSS.escape(profileId)}"]`);
    selections.push({ model_profile_id: profileId, role: role?.value || "" });
  }
  const stageOrder = { MAIN: 0, CRITIC: 1, AUDITOR: 2, SYNTHESIZER: 3 };
  return selections.sort((left, right) => (stageOrder[left.role] ?? 3) - (stageOrder[right.role] ?? 3));
}

function validateOrchestraSelection() {
  const selections = selectedOrchestraModels();
  if (selections.length < 2 || selections.length > 5) {
    throw new Error("Select between two and five models.");
  }
  if (selections.some((selection) => !selection.role)) {
    throw new Error("Assign an explicit allowed role to every selected model.");
  }
  if (selections.filter((selection) => selection.role === "MAIN").length !== 1) {
    throw new Error("Exactly one selected model must be MAIN.");
  }
  if (!selections.some((selection) => ["CRITIC", "AUDITOR"].includes(selection.role))) {
    throw new Error("Select at least one CRITIC or AUDITOR.");
  }
  return selections;
}

function updateOrchestraSelectionState() {
  const count = selectedOrchestraModels().length;
  elements.orchestraSelectionCount.textContent = `${count} selected`;
}

function invalidateOrchestraPreview(message = "Preview required") {
  state.orchestraPreview = null;
  state.orchestraPreviewHash = "";
  elements.orchestraPreviewHash.textContent = "missing";
  elements.orchestraConfirmationHash.value = "";
  elements.orchestraConfirmPreview.checked = false;
  elements.runOrchestra.disabled = true;
  elements.runOrchestra.className = "button button-disabled";
  elements.orchestraLiveStatus.textContent = message;
  elements.orchestraLiveStatus.className = "badge badge-blocked";
}

function updateRunOrchestraButton() {
  const exactMatch =
    Boolean(state.orchestraPreviewHash) &&
    elements.orchestraConfirmationHash.value.trim() === state.orchestraPreviewHash &&
    elements.orchestraConfirmPreview.checked;
  elements.runOrchestra.disabled = !exactMatch;
  elements.runOrchestra.className = exactMatch ? "button button-primary" : "button button-disabled";
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

async function refreshOrchestraConfiguration() {
  const [connectionsPayload, profilesPayload, modelsPayload] = await Promise.all([
    jsonFetch("/api/provider-connections"),
    jsonFetch("/api/model-profiles"),
    jsonFetch("/api/orchestra/models"),
  ]);
  state.providerConnections = collectionFromPayload(connectionsPayload, "connections", "provider_connections");
  state.modelProfiles = collectionFromPayload(profilesPayload, "model_profiles", "profiles", "models");
  state.orchestraModels = collectionFromPayload(modelsPayload, "models", "rows", "model_profiles");
  if (state.orchestraModels.length === 0 && state.modelProfiles.length > 0) {
    state.orchestraModels = state.modelProfiles;
  }
  populateModelConnectionSelect();
  renderOrchestraModels();
}

async function saveProviderConnection(event) {
  event.preventDefault();
  const apiKey = elements.providerApiKey.value;
  elements.providerConnectionFormStatus.textContent = "Saving connection locally.";
  try {
    await jsonFetch("/api/provider-connections", {
      method: "POST",
      body: JSON.stringify({
        connection_id: elements.providerConnectionId.value.trim(),
        display_name: elements.providerConnectionName.value.trim(),
        api_style: elements.providerApiStyle.value,
        base_url: elements.providerBaseUrl.value.trim(),
        api_key: apiKey,
      }),
    });
    elements.providerConnectionFormStatus.textContent =
      `Connection ${elements.providerConnectionId.value.trim()} saved. Credential status is masked.`;
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.providerConnectionFormStatus.textContent = `Connection was not saved: ${redactedError(error, apiKey)}`;
  } finally {
    elements.providerApiKey.value = "";
  }
}

async function saveModelProfile(event) {
  event.preventDefault();
  const allowedRoles = [...elements.modelAllowedRoles.selectedOptions].map((option) => option.value);
  elements.modelProfileFormStatus.textContent = "Saving model profile locally.";
  try {
    await jsonFetch("/api/model-profiles", {
      method: "POST",
      body: JSON.stringify({
        model_profile_id: elements.modelProfileId.value.trim(),
        connection_id: elements.modelProfileConnection.value,
        display_name: elements.modelProfileName.value.trim(),
        remote_model_id: elements.modelRemoteId.value.trim(),
        allowed_roles: allowedRoles,
      }),
    });
    elements.modelProfileFormStatus.textContent = `Model ${elements.modelProfileId.value.trim()} saved.`;
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.modelProfileFormStatus.textContent = `Model was not saved: ${String(error)}`;
  }
}

async function disableConnection(connectionIdValue) {
  invalidateOrchestraPreview("Connection state changed; generate a new preview.");
  try {
    await jsonFetch("/api/provider-connections/disable", {
      method: "POST",
      body: JSON.stringify({ connection_id: connectionIdValue }),
    });
    elements.providerConnectionFormStatus.textContent = `Connection ${connectionIdValue} disabled.`;
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.providerConnectionFormStatus.textContent = `Connection was not disabled: ${String(error)}`;
  }
}

async function disableModelProfile(profileId) {
  invalidateOrchestraPreview("Model state changed; generate a new preview.");
  try {
    await jsonFetch("/api/model-profiles/disable", {
      method: "POST",
      body: JSON.stringify({ model_profile_id: profileId }),
    });
    elements.modelProfileFormStatus.textContent = `Model ${profileId} disabled.`;
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.modelProfileFormStatus.textContent = `Model was not disabled: ${String(error)}`;
  }
}

async function testConnection(model) {
  const profileId = modelProfileId(model);
  const selectedConnectionId = modelConnectionId(model);
  elements.orchestraLiveStatus.textContent = `Testing ${model.display_name || profileId}`;
  elements.orchestraLiveStatus.className = "badge";
  try {
    const payload = await jsonFetch("/api/provider-connections/test", {
      method: "POST",
      body: JSON.stringify({
        connection_id: selectedConnectionId,
        model_profile_id: profileId,
        explicit_operator_action: true,
      }),
    });
    elements.orchestraLiveStatus.textContent = payload.success === false ? "Connection test failed" : "Connection test complete";
    renderSafeJson(elements.orchestraLiveResult, payload);
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.orchestraLiveStatus.textContent = `Connection test blocked: ${String(error)}`;
    elements.orchestraLiveStatus.className = "badge badge-blocked";
  }
}

async function previewOrchestraPlan() {
  const sourcePrompt = elements.orchestraPrompt.value.trim();
  if (!sourcePrompt) {
    elements.orchestraLiveStatus.textContent = "Enter a human prompt before previewing.";
    return;
  }
  try {
    const selections = validateOrchestraSelection();
    const payload = await jsonFetch("/api/orchestra/preview", {
      method: "POST",
      body: JSON.stringify({ source_prompt: sourcePrompt, selections }),
    });
    const preview = payload.preview || payload;
    const previewHash = String(preview.preview_hash || payload.preview_hash || "").trim();
    if (!previewHash) {
      throw new Error("Preview response did not contain preview_hash.");
    }
    state.orchestraPreview = preview;
    state.orchestraPreviewHash = previewHash;
    elements.orchestraPreviewHash.textContent = previewHash;
    elements.orchestraConfirmationHash.value = "";
    elements.orchestraConfirmPreview.checked = false;
    elements.orchestraLiveStatus.textContent = "Non-authoritative plan preview ready for human review";
    elements.orchestraLiveStatus.className = "badge";
    elements.runOrchestra.disabled = true;
    elements.runOrchestra.className = "button button-disabled";
    renderSafeJson(elements.orchestraLiveResult, payload);
  } catch (error) {
    invalidateOrchestraPreview(`Preview blocked: ${String(error)}`);
  }
}

async function runOrchestra() {
  const confirmationHash = elements.orchestraConfirmationHash.value.trim();
  if (
    !state.orchestraPreviewHash ||
    confirmationHash !== state.orchestraPreviewHash ||
    !elements.orchestraConfirmPreview.checked
  ) {
    invalidateOrchestraPreview("Exact preview confirmation is required.");
    return;
  }

  elements.runOrchestra.disabled = true;
  elements.orchestraLiveStatus.textContent = "Running one bounded Orchestra session";
  elements.orchestraLiveStatus.className = "badge";
  try {
    const payload = await jsonFetch("/api/orchestra/run", {
      method: "POST",
      body: JSON.stringify({
        preview_hash: state.orchestraPreviewHash,
        confirmation_hash: confirmationHash,
        confirmed_preview_hash: confirmationHash,
        explicit_run_action: true,
      }),
    });
    if (payload.ok === false) {
      const failed = payload.failed_stage || {};
      elements.orchestraLiveStatus.textContent =
        `Stage failed safely: ${failed.operator_role || "unknown"} / ${failed.model_profile_id || "unknown"}. ` +
        "The session was consumed; the operator may create a new preview.";
      elements.orchestraLiveStatus.className = "badge badge-blocked";
      renderSafeJson(elements.orchestraLiveResult, payload);
      state.orchestraPreview = null;
      state.orchestraPreviewHash = "";
      elements.orchestraConfirmationHash.value = "";
      elements.orchestraConfirmPreview.checked = false;
      return;
    }
    elements.orchestraLiveStatus.textContent = "Session complete — draft requires human review";
    renderSafeJson(elements.orchestraLiveResult, payload);
    state.orchestraPreview = null;
    state.orchestraPreviewHash = "";
    elements.orchestraConfirmationHash.value = "";
    elements.orchestraConfirmPreview.checked = false;
  } catch (error) {
    elements.orchestraLiveStatus.textContent = `Session blocked or failed: ${String(error)}`;
    elements.orchestraLiveStatus.className = "badge badge-blocked";
  }
}

function renderSafeJson(element, payload) {
  const serialized = JSON.stringify(safeUiPayload(payload), null, 2);
  element.textContent = serialized.length > 12000 ? `${serialized.substring(0, 12000)}\n[display truncated]` : serialized;
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
  try {
    await refreshOrchestraConfiguration();
  } catch (error) {
    elements.orchestraLiveStatus.textContent = `User configuration unavailable: ${String(error)}`;
    elements.orchestraLiveStatus.className = "badge badge-blocked";
  }
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

elements.providerConnectionForm.addEventListener("submit", saveProviderConnection);
elements.modelProfileForm.addEventListener("submit", saveModelProfile);
elements.refreshOrchestraModels.addEventListener("click", async () => {
  try {
    await refreshOrchestraConfiguration();
    elements.orchestraLiveStatus.textContent = "Saved user models reloaded";
    elements.orchestraLiveStatus.className = "badge";
  } catch (error) {
    elements.orchestraLiveStatus.textContent = `Reload blocked: ${String(error)}`;
    elements.orchestraLiveStatus.className = "badge badge-blocked";
  }
});
elements.previewOrchestraPlan.addEventListener("click", previewOrchestraPlan);
elements.orchestraConfirmationHash.addEventListener("input", updateRunOrchestraButton);
elements.orchestraConfirmPreview.addEventListener("change", updateRunOrchestraButton);
elements.orchestraPrompt.addEventListener("input", () => {
  if (state.orchestraPreviewHash) {
    invalidateOrchestraPreview("Prompt changed; generate a new preview.");
  }
});
elements.runOrchestra.addEventListener("click", runOrchestra);

renderPresetExamples();

refreshAll().catch((error) => {
  setConnectionStatus("error", "error");
  elements.disabledReason.textContent = String(error);
});
