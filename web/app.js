const state = {
  currentModel: "",
  scenario: null,
};

const elements = {
  modelSelect: document.querySelector("#model-select"),
  modelPicker: document.querySelector("#model-picker"),
  currentModelBadge: document.querySelector("#current-model-badge"),
  modelNote: document.querySelector("#model-note"),
  chatLog: document.querySelector("#chat-log"),
  promptInput: document.querySelector("#prompt-input"),
  composer: document.querySelector("#composer"),
  sessionModel: document.querySelector("#session-model"),
  sessionSummary: document.querySelector("#session-summary"),
  statusCwd: document.querySelector("#status-cwd"),
  statusBrowser: document.querySelector("#status-browser"),
  statusUrl: document.querySelector("#status-url"),
  statusVault: document.querySelector("#status-vault"),
  metricTools: document.querySelector("#metric-tools"),
  metricCommands: document.querySelector("#metric-commands"),
  metricOutputs: document.querySelector("#metric-outputs"),
  viewTitle: document.querySelector("#view-title"),
  reviewForm: document.querySelector("#review-form"),
  reviewInput: document.querySelector("#review-input"),
  reviewScenarioTitle: document.querySelector("#review-scenario-title"),
  reviewScenarioMeta: document.querySelector("#review-scenario-meta"),
  reviewPrompt: document.querySelector("#review-prompt"),
  reviewAsOf: document.querySelector("#review-as-of"),
  reviewEvidence: document.querySelector("#review-evidence"),
  reviewRequestStatus: document.querySelector("#review-request-status"),
  reviewValueStatus: document.querySelector("#review-value-status"),
  reviewDecision: document.querySelector("#review-decision"),
  reviewCriticalCount: document.querySelector("#review-critical-count"),
  reviewWarningCount: document.querySelector("#review-warning-count"),
  reviewInfoCount: document.querySelector("#review-info-count"),
  reviewFindings: document.querySelector("#review-findings"),
  reviewEvidenceDigest: document.querySelector("#review-evidence-digest"),
  reviewSnapshotHash: document.querySelector("#review-snapshot-hash"),
  reviewNextStep: document.querySelector("#review-next-step"),
};

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `Request failed: ${response.status}`);
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
  state.currentModel = status.model;
  elements.currentModelBadge.textContent = status.model;
  elements.sessionModel.textContent = status.model;
  elements.sessionSummary.textContent = status.browser_active
    ? "Browser session is active and ready for operator-approved actions."
    : "Browser is idle. Local routing, evidence review, shell, and filesystem tools are ready.";
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
  hydrateModelSelect(payload.available_models, payload.model);
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

function hydrateModelSelect(availableModels, currentModel) {
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
  hydrateModelPicker(choices, currentModel);
}

function hydrateModelPicker(choices, currentModel) {
  elements.modelPicker.innerHTML = "";
  for (const choice of choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "model-pill";
    button.dataset.model = choice.value;
    button.textContent = choice.label;
    button.title = choice.value;
    button.setAttribute("aria-pressed", String(choice.value === currentModel));
    if (choice.value === currentModel) {
      button.classList.add("model-pill-active");
    }
    button.addEventListener("click", async () => {
      elements.modelSelect.value = choice.value;
      try {
        await switchModel();
      } catch (error) {
        elements.modelNote.textContent = String(error);
      }
    });
    elements.modelPicker.appendChild(button);
  }
}

async function switchModel() {
  const model = elements.modelSelect.value;
  elements.modelNote.textContent = `Switching to ${model}…`;
  const payload = await jsonFetch("/api/model", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
  elements.modelNote.textContent =
    payload.notice || `Assistant model switched to ${payload.model}. Evidence review remains local.`;
  applyStatus(payload.status);
  hydrateModelSelect(payload.status.available_models, payload.status.model);
}

async function sendPrompt(prompt) {
  addMessage("You", prompt);
  const payload = await jsonFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
  addMessage("AOIA-Core", payload.transcript);
  applyStatus(payload.status);
}

function setView(view) {
  for (const tab of document.querySelectorAll(".view-tab")) {
    const selected = tab.dataset.view === view;
    tab.classList.toggle("view-tab-active", selected);
    tab.setAttribute("aria-selected", String(selected));
  }
  document.querySelector("#assistant-view").hidden = view !== "assistant";
  document.querySelector("#review-view").hidden = view !== "review";
  elements.viewTitle.textContent = view === "review" ? "Dated evidence review" : "Assistant runtime";
}

function renderEvidence(evidence) {
  elements.reviewEvidence.innerHTML = "";
  const template = document.querySelector("#evidence-template");
  for (const source of evidence || []) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".evidence-title").textContent = source.title;
    node.querySelector(".evidence-meta").textContent =
      `${source.publisher} · effective ${source.effective_from} · checked ${source.checked_at}`;
    node.querySelector(".evidence-fact").textContent = source.fact;
    const link = node.querySelector(".evidence-link");
    link.href = source.url;
    link.setAttribute("aria-label", `Open official source: ${source.title}`);
    elements.reviewEvidence.appendChild(node);
  }
}

async function loadReviewScenario() {
  const scenario = await jsonFetch("/api/review/scenario");
  state.scenario = scenario;
  elements.reviewScenarioTitle.textContent = scenario.title;
  elements.reviewScenarioMeta.textContent =
    `${scenario.jurisdiction} · ${scenario.domain} · ${scenario.risk_domain}`;
  elements.reviewPrompt.textContent = scenario.prompt;
  elements.reviewInput.value = scenario.candidate_answer;
  elements.reviewAsOf.textContent = `as of ${scenario.as_of_date}`;
  renderEvidence(scenario.evidence);
}

function readableStatus(status) {
  return String(status || "unknown")
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function renderReview(result) {
  elements.reviewValueStatus.textContent = readableStatus(result.value_status);
  elements.reviewDecision.textContent = readableStatus(result.decision_state);
  elements.reviewDecision.className = "badge badge-warning";
  elements.reviewCriticalCount.textContent = String(result.severity_counts.critical);
  elements.reviewWarningCount.textContent = String(result.severity_counts.warning);
  elements.reviewInfoCount.textContent = String(result.severity_counts.info);
  elements.reviewEvidenceDigest.textContent = result.evidence_digest;
  elements.reviewSnapshotHash.textContent = result.snapshot_hash;
  elements.reviewNextStep.textContent = result.operator_next_step;
  renderEvidence(result.evidence);

  elements.reviewFindings.innerHTML = "";
  const template = document.querySelector("#finding-template");
  for (const finding of result.findings) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.classList.add(`finding-${finding.severity}`);
    const severity = node.querySelector(".finding-severity");
    severity.textContent = finding.severity;
    severity.classList.add(`severity-${finding.severity}`);
    node.querySelector(".finding-title").textContent = finding.title;
    node.querySelector(".finding-detail").textContent = finding.detail;
    elements.reviewFindings.appendChild(node);
  }
}

async function runReview() {
  const candidateAnswer = elements.reviewInput.value.trim();
  if (!candidateAnswer) {
    elements.reviewRequestStatus.textContent = "Candidate answer is required.";
    return;
  }
  elements.reviewRequestStatus.textContent = "Running deterministic comparison…";
  const result = await jsonFetch("/api/review", {
    method: "POST",
    body: JSON.stringify({ candidate_answer: candidateAnswer }),
  });
  renderReview(result);
  elements.reviewRequestStatus.textContent =
    `Completed locally as ${result.review_id}; no provider or network call was used.`;
}

document.querySelector("#switch-model").addEventListener("click", async () => {
  try {
    await switchModel();
  } catch (error) {
    elements.modelNote.textContent = String(error);
  }
});

document.querySelector("#refresh-status").addEventListener("click", async () => {
  try {
    await refreshStatus();
  } catch (error) {
    addMessage("System", `Refresh failed: ${error}`);
  }
});

for (const tab of document.querySelectorAll(".view-tab")) {
  tab.addEventListener("click", () => setView(tab.dataset.view));
}

for (const button of document.querySelectorAll(".quick-action")) {
  button.addEventListener("click", () => {
    setView("assistant");
    elements.promptInput.value = button.dataset.prompt || "";
    elements.promptInput.focus();
  });
}

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
    addMessage("System", `Request failed: ${error}`);
  }
});

elements.promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

elements.reviewForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await runReview();
  } catch (error) {
    elements.reviewRequestStatus.textContent = `Review failed: ${error}`;
  }
});

document.querySelector("#load-stale").addEventListener("click", () => {
  if (state.scenario) {
    elements.reviewInput.value = state.scenario.candidate_answer;
  }
});

document.querySelector("#load-corrected").addEventListener("click", () => {
  if (state.scenario) {
    elements.reviewInput.value = state.scenario.corrected_example;
  }
});

async function bootstrap() {
  addMessage(
    "System",
    "AOIA-Core is ready. Assistant actions use the existing runtime boundaries; dated evidence review runs locally without a model call."
  );
  const [statusResult, scenarioResult] = await Promise.allSettled([
    refreshStatus(),
    loadReviewScenario(),
  ]);
  if (statusResult.status === "rejected") {
    addMessage("System", `Runtime startup failed: ${statusResult.reason}`);
  }
  if (scenarioResult.status === "rejected") {
    elements.reviewRequestStatus.textContent = `Evidence registry failed to load: ${scenarioResult.reason}`;
  }
}

bootstrap();
