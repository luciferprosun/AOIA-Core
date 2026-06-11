const state = {
  currentLegacyModel: "",
  catalogModels: [],
  selectedModel: {
    providerId: "",
    modelId: "",
    source: "catalog",
    mode: "proposal_only",
  },
  lastProposal: null,
};

const PROVIDER_LABELS = {
  gemini: "Gemini",
  openrouter: "OpenRouter",
  local: "Local",
  disabled: "Disabled",
};

const TASK_MODE_LABELS = {
  PUBLIC_DEV: "Public development",
  CODE: "Code review",
  AUDIT: "Audit",
  RESEARCH: "Research",
  SENSITIVE: "Sensitive",
  CANONICAL: "Canonical",
};

const elements = {
  modelSelect: document.querySelector("#model-select"),
  modelPicker: document.querySelector("#model-picker"),
  currentModelBadge: document.querySelector("#current-model-badge"),
  legacyModelBadge: document.querySelector("#legacy-model-badge"),
  sidebarSelectedModel: document.querySelector("#sidebar-selected-model"),
  modelNote: document.querySelector("#model-note"),
  chatLog: document.querySelector("#chat-log"),
  promptInput: document.querySelector("#prompt-input"),
  composer: document.querySelector("#composer"),
  criticTransform: document.querySelector("#critic-transform"),
  cptStatus: document.querySelector("#cpt-status"),
  sessionModel: document.querySelector("#session-model"),
  sessionSummary: document.querySelector("#session-summary"),
  statusCwd: document.querySelector("#status-cwd"),
  statusBrowser: document.querySelector("#status-browser"),
  statusUrl: document.querySelector("#status-url"),
  statusVault: document.querySelector("#status-vault"),
  metricTools: document.querySelector("#metric-tools"),
  metricCommands: document.querySelector("#metric-commands"),
  metricOutputs: document.querySelector("#metric-outputs"),
  catalogStatus: document.querySelector("#catalog-status"),
  catalogNotice: document.querySelector("#catalog-notice"),
  modelCatalog: document.querySelector("#model-catalog"),
  memoryHatsStatus: document.querySelector("#memory-hats-status"),
  memoryHatsList: document.querySelector("#memory-hats-list"),
  providerConfigStatus: document.querySelector("#provider-config-status"),
  routerProviderSelect: document.querySelector("#router-provider-select"),
  routerModelSelect: document.querySelector("#router-model-select"),
  routerTaskMode: document.querySelector("#router-task-mode"),
  routerModeLabel: document.querySelector("#router-mode-label"),
  routerPrompt: document.querySelector("#router-prompt"),
  routerHumanApproval: document.querySelector("#router-human-approval"),
  approveAndCallProvider: document.querySelector("#approve-and-call-provider"),
  routerSimpleResult: document.querySelector("#router-simple-result"),
  routerResultStatus: document.querySelector("#router-result-status"),
  routerResultReason: document.querySelector("#router-result-reason"),
  routerCallNote: document.querySelector("#router-call-note"),
  routerProposalResult: document.querySelector("#router-proposal-result"),
  routerCallResult: document.querySelector("#router-call-result"),
  auditProviderCallPermitted: document.querySelector("#audit-provider-call-permitted"),
  auditHumanApproved: document.querySelector("#audit-human-approved"),
  auditOutputTrusted: document.querySelector("#audit-output-trusted"),
  auditFallback: document.querySelector("#audit-fallback"),
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

function addMessage(role, body) {
  const template = document.querySelector("#message-template");
  const node = template.content.firstElementChild.cloneNode(true);
  node.querySelector(".message-role").textContent = role;
  node.querySelector(".message-body").textContent = body || "(empty)";
  if (role === "You") {
    node.classList.add("message-user");
  }
  elements.chatLog.appendChild(node);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function applyStatus(status) {
  state.currentLegacyModel = status.model;
  elements.legacyModelBadge.textContent = status.model;
  elements.sessionModel.textContent = status.model;
  elements.sessionSummary.textContent = status.browser_active
    ? "Browser session is active in the legacy runtime path."
    : "Legacy runtime is idle. Controlled router selection above is separate.";
  elements.statusCwd.textContent = status.cwd;
  elements.statusBrowser.textContent = status.browser_active ? "active" : "inactive";
  elements.statusUrl.textContent = status.current_url || "(none)";
  elements.statusVault.textContent = status.vault_dir;
  elements.metricTools.textContent = String((status.tools || []).length);
  elements.metricCommands.textContent = String((status.previous_commands || []).length);
  elements.metricOutputs.textContent = String((status.recent_outputs || []).length);
}

async function refreshStatus() {
  const payload = await jsonFetch("/api/status");
  applyStatus(payload);
  hydrateLegacyModelSelect(payload.available_models, payload.model);
}

async function refreshModelCatalog() {
  const payload = await jsonFetch("/api/model-catalog");
  hydrateModelCatalog(payload);
}

async function refreshProviderConfigStatus() {
  const payload = await jsonFetch("/api/provider-config-status");
  elements.providerConfigStatus.textContent = [
    `Gemini: ${payload.gemini_configured ? "Configured" : "Not configured"}`,
    `OpenRouter: ${payload.openrouter_configured ? "Configured" : "Not configured"}`,
  ].join(" / ");
}

async function refreshMemoryHats() {
  const payload = await jsonFetch("/api/memory-hats");
  renderMemoryHats(payload);
}

function providerLabel(providerId) {
  return PROVIDER_LABELS[providerId] || providerId || "Unknown provider";
}

function taskModeLabel(mode) {
  return TASK_MODE_LABELS[mode] || mode || "Unknown mode";
}

function friendlyModelLabel(model) {
  if (!model) {
    return "No catalog model selected.";
  }
  const provider = providerLabel(model.provider_id || model.providerId || "");
  const displayName = model.display_name || model.model_id || model.modelId || "";
  if (!displayName) {
    return provider;
  }
  return `${provider} - ${displayName}`;
}

function parseModelChoices(availableModels) {
  return (availableModels || []).map((line) => {
    const [aliasPart, modelPart] = line.split("->").map((item) => item.trim());
    return {
      label: aliasPart,
      value: modelPart,
    };
  });
}

function hydrateLegacyModelSelect(availableModels, currentModel) {
  const choices = parseModelChoices(availableModels);

  elements.modelSelect.innerHTML = "";
  for (const choice of choices) {
    const option = document.createElement("option");
    option.value = choice.value;
    option.textContent = `${choice.label} -> ${choice.value}`;
    option.selected = choice.value === currentModel;
    elements.modelSelect.appendChild(option);
  }

  if (!choices.some((choice) => choice.value === currentModel)) {
    const option = document.createElement("option");
    option.value = currentModel;
    option.textContent = currentModel;
    option.selected = true;
    elements.modelSelect.appendChild(option);
  }

  hydrateLegacyModelPicker(choices, currentModel);
}

function hydrateLegacyModelPicker(choices, currentModel) {
  elements.modelPicker.innerHTML = "";
  for (const choice of choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "model-pill";
    button.dataset.model = choice.value;
    button.textContent = choice.label;
    button.title = choice.value;
    if (choice.value === currentModel) {
      button.classList.add("model-pill-active");
      button.setAttribute("aria-pressed", "true");
    } else {
      button.setAttribute("aria-pressed", "false");
    }
    button.addEventListener("click", async () => {
      elements.modelSelect.value = choice.value;
      try {
        await switchLegacyModel();
      } catch (error) {
        elements.modelNote.textContent = String(error);
      }
    });
    elements.modelPicker.appendChild(button);
  }
}

function hydrateModelCatalog(payload) {
  elements.catalogStatus.textContent = payload.status
    ? policyStatusLabel({ status: payload.status })
    : "Preview only";
  elements.catalogNotice.textContent =
    payload.notice ||
    "Preview only - no provider calls. Human approval required before any future provider call.";
  state.catalogModels = payload.models || [];
  hydrateProviderSelect(state.catalogModels);
  renderModelCatalog(state.catalogModels);
}

function hydrateProviderSelect(models) {
  const providerIds = [...new Set((models || []).map((model) => model.provider_id))];
  elements.routerProviderSelect.innerHTML = "";
  for (const providerId of providerIds) {
    const option = document.createElement("option");
    option.value = providerId;
    option.textContent = providerLabel(providerId);
    elements.routerProviderSelect.appendChild(option);
  }
  if (providerIds.length > 0) {
    elements.routerProviderSelect.value = state.selectedModel.providerId || providerIds[0];
  }
  hydrateRouterModelSelect();
}

function hydrateRouterModelSelect() {
  const providerId = elements.routerProviderSelect.value;
  const models = state.catalogModels.filter((model) => model.provider_id === providerId);
  elements.routerModelSelect.innerHTML = "";
  for (const model of models) {
    const option = document.createElement("option");
    option.value = model.model_id;
    option.textContent = model.display_name || model.model_id;
    elements.routerModelSelect.appendChild(option);
  }
  if (models.length > 0) {
    const currentStillVisible = models.some((model) => model.model_id === state.selectedModel.modelId);
    elements.routerModelSelect.value = currentStillVisible ? state.selectedModel.modelId : models[0].model_id;
  }
  updateSelectedModelFromCatalog();
}

function updateSelectedModelFromCatalog() {
  const selectedCatalogModel = state.catalogModels.find(
    (model) =>
      model.provider_id === elements.routerProviderSelect.value &&
      model.model_id === elements.routerModelSelect.value
  );
  state.selectedModel = {
    providerId: elements.routerProviderSelect.value,
    modelId: elements.routerModelSelect.value,
    source: "catalog",
    mode: "proposal_only",
  };
  elements.currentModelBadge.textContent = selectedCatalogModel?.display_name || "Preview only";
  elements.sidebarSelectedModel.textContent = friendlyModelLabel(selectedCatalogModel);
  elements.routerModeLabel.textContent = "Proposal only";
  state.lastProposal = null;
  renderSimpleResult("blocked", "Prepare a model choice to review policy status.");
  updateAuditFields({});
  updateCallButtonState();
}

function renderModelCatalog(models) {
  elements.modelCatalog.innerHTML = "";

  for (const model of models || []) {
    const article = document.createElement("article");
    article.className = "catalog-card";

    const title = document.createElement("h4");
    title.textContent = model.display_name || model.model_id;

    const modelId = document.createElement("p");
    modelId.className = "catalog-model-id";
    modelId.textContent = model.model_id;

    const tags = document.createElement("div");
    tags.className = "catalog-tags";
    for (const value of [model.provider_class, model.trust_level, model.free_tier ? "FREE" : "", model.paid_tier ? "PAID" : ""]) {
      if (!value) {
        continue;
      }
      const tag = document.createElement("span");
      tag.className = "catalog-tag";
      tag.textContent = value;
      tags.appendChild(tag);
    }

    const flags = document.createElement("p");
    flags.className = "catalog-flags";
    flags.textContent = [
      model.enabled ? "enabled" : "disabled by default",
      model.allows_sensitive_tasks ? "sensitive allowed" : "no sensitive tasks",
      model.allows_canonical_tasks ? "canonical allowed" : "no canonical tasks",
    ].join(" / ");

    const notes = document.createElement("ul");
    notes.className = "catalog-notes";
    for (const note of model.notes || []) {
      const item = document.createElement("li");
      item.textContent = note;
      notes.appendChild(item);
    }

    article.append(title, modelId, tags, flags, notes);
    elements.modelCatalog.appendChild(article);
  }
}

function renderMemoryHats(payload) {
  const hats = payload.hats || [];
  elements.memoryHatsStatus.textContent = `${hats.length} hats`;
  elements.memoryHatsList.innerHTML = "";

  for (const hat of hats) {
    const article = document.createElement("article");
    article.className = "memory-hat-card";

    const title = document.createElement("h3");
    title.textContent = hat.name;

    const status = document.createElement("p");
    status.className = "memory-hat-status";
    status.textContent = hat.status;

    const purpose = document.createElement("p");
    purpose.className = "note";
    purpose.textContent = hat.purpose;

    const flags = document.createElement("p");
    flags.className = "catalog-flags";
    flags.textContent = [
      hat.domain,
      hat.execution_allowed ? "execution allowed" : "no execution",
      hat.human_review_required ? "human review required" : "human review not required",
    ].join(" / ");

    article.append(title, status, purpose, flags);
    elements.memoryHatsList.appendChild(article);
  }
}

function selectedRouterModel() {
  return {
    provider_id: state.selectedModel.providerId,
    model_id: state.selectedModel.modelId,
  };
}

function routerTaskSensitivity() {
  const mode = elements.routerTaskMode.value;
  if (mode === "CODE" || mode === "AUDIT" || mode === "RESEARCH") {
    return "INTERNAL_NON_CANONICAL";
  }
  return mode;
}

function renderJson(element, payload) {
  element.textContent = JSON.stringify(payload, null, 2);
}

function resultTone(statusKey) {
  if (statusKey === "allowed") {
    return "allowed";
  }
  if (statusKey === "requires-human-approval") {
    return "requires-human-approval";
  }
  if (statusKey === "rejected-by-policy") {
    return "rejected-by-policy";
  }
  return "blocked";
}

function renderSimpleResult(status, reason) {
  elements.routerResultStatus.textContent = status;
  elements.routerResultStatus.className = `result-status result-${resultTone(status)}`;
  elements.routerResultReason.textContent = reason;
}

function policyStatusLabel(decision) {
  if (!decision) {
    return "Blocked before provider call";
  }
  if (decision.status === "REQUIRES_HUMAN_APPROVAL") {
    return "Requires human approval";
  }
  if (decision.status === "REJECTED_BY_POLICY") {
    return "Rejected by policy";
  }
  if (decision.status === "ALLOWED") {
    return "Allowed";
  }
  return "Blocked";
}

function policyStatusKey(decision) {
  if (!decision) {
    return "blocked";
  }
  if (decision.status === "REQUIRES_HUMAN_APPROVAL") {
    return "requires-human-approval";
  }
  if (decision.status === "REJECTED_BY_POLICY") {
    return "rejected-by-policy";
  }
  if (decision.status === "ALLOWED") {
    return "allowed";
  }
  return "blocked";
}

function friendlyReason(decision) {
  const reason = decision?.reason || "Policy status is not available.";
  if (reason.includes("Generic OpenRouter free routes")) {
    return "OpenRouter Free is preview-only and cannot be called.";
  }
  if (reason.includes("Disabled or unknown")) {
    return "This provider is disabled or unknown.";
  }
  return reason;
}

function friendlyBoolean(value, trueLabel, falseLabel) {
  return value ? trueLabel : falseLabel;
}

function updateAuditFields(payload) {
  const proposal = payload.proposal || {};
  const decision = payload.decision || {};
  const approval = payload.approval || {};
  const providerCallPermitted =
    payload.provider_call_permitted ?? decision.provider_call_permitted ?? approval.provider_call_permitted ?? false;
  const humanApproved = approval.human_approved ?? elements.routerHumanApproval.checked;
  const outputTrusted = payload.output_trusted ?? false;
  const fallbackEnabled =
    proposal.automatic_fallback_permitted || decision.automatic_fallback_permitted || payload.automatic_fallback_used;

  elements.auditProviderCallPermitted.textContent = String(
    friendlyBoolean(providerCallPermitted, "Provider call is permitted", "Provider call is not permitted")
  );
  elements.auditHumanApproved.textContent = friendlyBoolean(
    humanApproved,
    "Human approval is granted",
    "Human approval is not granted"
  );
  elements.auditOutputTrusted.textContent = friendlyBoolean(
    outputTrusted,
    "Provider output is trusted",
    "Provider output is untrusted"
  );
  elements.auditFallback.textContent =
    fallbackEnabled ? "Automatic fallback is enabled" : "Automatic fallback is blocked";
}

function updateCallButtonState() {
  const decision = state.lastProposal?.decision;
  const proposalAllowed = decision?.status === "REQUIRES_HUMAN_APPROVAL";
  elements.approveAndCallProvider.disabled = !(proposalAllowed && elements.routerHumanApproval.checked);
  if (!decision) {
    elements.routerCallNote.textContent = "Provider call not enabled in this build.";
    return;
  }
  if (decision.status === "REJECTED_BY_POLICY") {
    elements.routerCallNote.textContent = "Provider call not enabled in this build.";
    return;
  }
  if (!elements.routerHumanApproval.checked) {
    elements.routerCallNote.textContent = "Human approval is required before any provider call.";
    return;
  }
  elements.routerCallNote.textContent = "One approved provider call is enabled for this selected model.";
}

async function createSelectionProposal() {
  const selected = selectedRouterModel();
  const payload = await jsonFetch("/api/model-selection/propose", {
    method: "POST",
    body: JSON.stringify({
      provider_id: selected.provider_id,
      model_id: selected.model_id,
      task_sensitivity: routerTaskSensitivity(),
      user_prompt: elements.routerPrompt.value,
    }),
  });
  state.lastProposal = payload;
  renderJson(elements.routerProposalResult, payload);
  renderSimpleResult(policyStatusKey(payload.decision), friendlyReason(payload.decision));
  elements.routerResultStatus.textContent = policyStatusLabel(payload.decision);
  updateAuditFields(payload);
  updateCallButtonState();
}

async function approveAndCallProviderOnce() {
  const selected = selectedRouterModel();
  const payload = await jsonFetch("/api/model-selection/approve-and-call", {
    method: "POST",
    body: JSON.stringify({
      provider_id: selected.provider_id,
      model_id: selected.model_id,
      task_sensitivity: routerTaskSensitivity(),
      user_prompt: elements.routerPrompt.value,
      human_approved: elements.routerHumanApproval.checked === true,
    }),
  });
  renderJson(elements.routerCallResult, payload);
  renderSimpleResult(
    payload.call_made ? "allowed" : policyStatusKey(payload.decision),
    payload.error || friendlyReason(payload.decision)
  );
  elements.routerResultStatus.textContent = payload.call_made ? "Allowed" : policyStatusLabel(payload.decision);
  updateAuditFields(payload);
}

async function switchLegacyModel() {
  const model = elements.modelSelect.value;
  elements.modelNote.textContent = `Switching legacy chat model to ${model}...`;
  const payload = await jsonFetch("/api/model", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
  elements.modelNote.textContent = payload.notice || `Legacy chat model switched to ${payload.model}`;
  applyStatus(payload.status);
  hydrateLegacyModelSelect(payload.status.available_models, payload.status.model);
}

async function sendPrompt(prompt) {
  addMessage("You", prompt);
  const payload = await jsonFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
  addMessage("Agent", payload.transcript);
  applyStatus(payload.status);
}

async function transformComposerPrompt() {
  const prompt = elements.promptInput.value;
  if (!prompt.trim()) {
    elements.cptStatus.textContent = "Enter a prompt before running Critic Transform.";
    return;
  }

  elements.criticTransform.disabled = true;
  elements.cptStatus.textContent = "CPT transform running locally. Manual send required.";
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
      "CPT transformed locally.",
      payload.record.canonical_status,
      "Human review required.",
      "No provider call during transform.",
      "Manual send required.",
    ].join(" ");
  } catch (error) {
    elements.cptStatus.textContent = String(error);
  } finally {
    elements.criticTransform.disabled = false;
  }
}

document.querySelector("#switch-model").addEventListener("click", async () => {
  try {
    await switchLegacyModel();
  } catch (error) {
    elements.modelNote.textContent = String(error);
  }
});

document.querySelector("#refresh-status").addEventListener("click", async () => {
  try {
    await refreshStatus();
    await refreshModelCatalog();
    await refreshMemoryHats();
    await refreshProviderConfigStatus();
  } catch (error) {
    addMessage("System", `Refresh failed: ${error}`);
  }
});

elements.criticTransform.addEventListener("click", async () => {
  await transformComposerPrompt();
});

elements.routerProviderSelect.addEventListener("change", hydrateRouterModelSelect);
elements.routerModelSelect.addEventListener("change", updateSelectedModelFromCatalog);
elements.routerTaskMode.addEventListener("change", () => {
  state.lastProposal = null;
  renderSimpleResult("blocked", "Prepare a model choice to review policy status.");
  elements.routerResultStatus.textContent = "Blocked before provider call";
  updateCallButtonState();
});
elements.routerHumanApproval.addEventListener("change", () => {
  updateAuditFields(state.lastProposal || {});
  updateCallButtonState();
});

document.querySelector("#create-selection-proposal").addEventListener("click", async () => {
  try {
    await createSelectionProposal();
  } catch (error) {
    renderJson(elements.routerProposalResult, { ok: false, error: String(error) });
    renderSimpleResult("blocked", String(error));
    elements.routerResultStatus.textContent = "Blocked";
  }
});

document.querySelector("#approve-and-call-provider").addEventListener("click", async () => {
  try {
    await approveAndCallProviderOnce();
  } catch (error) {
    const payload = { ok: false, error: String(error), call_made: false, output_trusted: false };
    renderJson(elements.routerCallResult, payload);
    renderSimpleResult("blocked", String(error));
    elements.routerResultStatus.textContent = "Blocked";
    updateAuditFields(payload);
  }
});

elements.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = elements.promptInput.value.trim();
  if (!prompt) {
    return;
  }
  elements.promptInput.value = "";
  try {
    await sendPrompt(prompt);
  } catch (error) {
    addMessage("System", `Legacy request failed: ${error}`);
  }
});

elements.promptInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

async function bootstrap() {
  addMessage(
    "System",
    "Controlled Model Router is ready. Use the main router controls for proposal-only model review."
  );
  try {
    await refreshStatus();
    await refreshModelCatalog();
    await refreshMemoryHats();
    await refreshProviderConfigStatus();
  } catch (error) {
    addMessage("System", `Startup failed: ${error}`);
  }
}

bootstrap();
