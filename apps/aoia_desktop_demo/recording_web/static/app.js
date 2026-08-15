"use strict";

const elements = {
  model: document.querySelector("#model-select"),
  cplToggle: document.querySelector("#cpl-toggle"),
  knowledgeToggle: document.querySelector("#knowledge-toggle"),
  cplState: document.querySelector("#cpl-state"),
  knowledgeState: document.querySelector("#knowledge-state"),
  knowledgeIndicator: document.querySelector("#knowledge-indicator"),
  compositionWarning: document.querySelector("#composition-warning"),
  cplPanel: document.querySelector("#cpl-panel"),
  observerGrid: document.querySelector("#observer-grid"),
  history: document.querySelector("#chat-history"),
  emptyChat: document.querySelector("#empty-chat"),
  status: document.querySelector("#run-status-text"),
  statusDot: document.querySelector("#run-status .status-dot"),
  prompt: document.querySelector("#prompt-input"),
  send: document.querySelector("#send-button"),
  preset: document.querySelector("#preset-button"),
  clear: document.querySelector("#clear-button"),
};

const state = {
  csrf: "",
  models: [],
  roles: [],
  demoPrompt: "",
  busy: false,
  runId: null,
};

function setStatus(text, kind = "neutral") {
  elements.status.textContent = text;
  elements.statusDot.className = `status-dot ${kind}`;
}

function setBusy(value) {
  state.busy = value;
  elements.model.disabled = value || state.models.length === 0;
  elements.cplToggle.disabled = value;
  elements.knowledgeToggle.disabled = value;
  elements.prompt.disabled = value;
  elements.clear.disabled = value;
  elements.preset.disabled = value;
  document.querySelectorAll(".observer-model").forEach((select) => {
    select.disabled = value;
  });
  updateSendState();
}

function updateSendState() {
  const compositionUnavailable = elements.cplToggle.checked && elements.knowledgeToggle.checked;
  elements.send.disabled = state.busy || state.models.length === 0 || compositionUnavailable;
}

function renderModeState() {
  const cpl = elements.cplToggle.checked;
  const knowledge = elements.knowledgeToggle.checked;
  elements.cplState.textContent = cpl ? "ON" : "OFF";
  elements.knowledgeState.textContent = knowledge ? "ON" : "OFF";
  elements.cplPanel.hidden = !cpl;
  elements.knowledgeIndicator.hidden = !knowledge;
  elements.compositionWarning.hidden = !(cpl && knowledge);
  updateSendState();
}

function createModelOption(model) {
  const option = document.createElement("option");
  option.value = model.id;
  option.textContent = model.label;
  return option;
}

function renderObservers() {
  elements.observerGrid.replaceChildren();
  state.roles.forEach((role, offset) => {
    const index = offset + 1;
    const card = document.createElement("article");
    card.className = "observer-card";
    card.dataset.slot = `observer-${index}`;

    const heading = document.createElement("h3");
    heading.textContent = `OBSERVER ${index}`;
    const roleElement = document.createElement("p");
    roleElement.className = "observer-role";
    roleElement.textContent = `Role: ${role}`;
    const select = document.createElement("select");
    select.className = "observer-model";
    select.dataset.test = `observer-${index}-model`;
    select.setAttribute("aria-label", `Observer ${index} model`);
    state.models.forEach((model) => select.append(createModelOption(model)));
    select.value = elements.model.value;
    const status = document.createElement("p");
    status.className = "observer-state";
    status.textContent = "READY";
    const summary = document.createElement("p");
    summary.className = "observer-summary";
    summary.textContent = "Waiting for an explicit CPL run.";
    card.append(heading, roleElement, select, status, summary);
    elements.observerGrid.append(card);
  });
}

function updateObservers(observers, activeStage = "") {
  state.roles.forEach((_role, offset) => {
    const index = offset + 1;
    const card = elements.observerGrid.querySelector(`[data-slot="observer-${index}"]`);
    if (!card) return;
    const projection = observers.find((value) => value.slot_id === `observer-${index}`);
    const status = card.querySelector(".observer-state");
    const summary = card.querySelector(".observer-summary");
    if (projection) {
      status.textContent = projection.state;
      summary.textContent = projection.summary;
    } else if (activeStage === `observer-${index}`) {
      status.textContent = "REVIEWING";
      summary.textContent = "Reviewing the internal draft and prior bounded metadata.";
    } else {
      status.textContent = "QUEUED";
      summary.textContent = "Waiting for the historical sequential flow.";
    }
  });
}

function appendMessage(kind, speaker, text, metadata = []) {
  if (elements.emptyChat) {
    elements.emptyChat.remove();
    elements.emptyChat = null;
  }
  const article = document.createElement("article");
  article.className = `message ${kind}`;
  article.dataset.test = `${kind}-message`;
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = speaker;
  const body = document.createElement("p");
  body.className = "message-body";
  body.textContent = text;
  article.append(label, body);
  if (metadata.length) {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    metadata.forEach((item) => {
      const badge = document.createElement("span");
      badge.textContent = item.text;
      if (item.active) badge.className = "active";
      meta.append(badge);
    });
    article.append(meta);
  }
  elements.history.append(article);
  elements.history.scrollTop = elements.history.scrollHeight;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method && options.method !== "GET") {
    headers.set("X-AIOA-CSRF", state.csrf);
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {credentials: "same-origin", ...options, headers});
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "LOCAL_REQUEST_FAILED");
  }
  return payload;
}

async function pollRun(runId) {
  for (let count = 0; count < 420; count += 1) {
    const run = await api(`/api/runs/${encodeURIComponent(runId)}`);
    setStatus(run.status_text, run.state === "FAILED" ? "error" : "busy");
    if (run.critical_loop) updateObservers(run.observers || [], run.stage);
    if (run.state === "COMPLETED") return run;
    if (run.state === "FAILED") throw new Error(run.error_code || "RUN_FAILED");
    await new Promise((resolve) => window.setTimeout(resolve, 750));
  }
  throw new Error("RUN_TIMEOUT");
}

function selectedObserverModels() {
  return Array.from(document.querySelectorAll(".observer-model"), (select) => select.value);
}

async function sendPrompt() {
  if (state.busy) return;
  const prompt = elements.prompt.value.trim();
  if (!prompt) {
    elements.prompt.focus();
    return;
  }
  const modelId = elements.model.value;
  const selectedModel = state.models.find((model) => model.id === modelId);
  const criticalLoop = elements.cplToggle.checked;
  const germanLaw = elements.knowledgeToggle.checked;
  appendMessage("user", "You", prompt);
  elements.prompt.value = "";
  setBusy(true);
  setStatus("Submitting one bounded real provider run...", "busy");
  if (criticalLoop) updateObservers([], "primary-draft");
  try {
    const started = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        model_id: modelId,
        critical_loop: criticalLoop,
        german_law: germanLaw,
        observer_models: criticalLoop ? selectedObserverModels() : [],
      }),
    });
    state.runId = started.run_id;
    const completed = await pollRun(started.run_id);
    const result = completed.result;
    const metadata = [{text: selectedModel ? selectedModel.label : modelId, active: false}];
    if (germanLaw) {
      appendMessage(
        "assistant-primary",
        `${selectedModel ? selectedModel.label : "Gemma"} — Primary · UNVERIFIED`,
        result.primary_response,
        [
          {text: "PRIMARY", active: false},
          {text: "UNVERIFIED", active: false},
        ],
      );
      metadata.push(
        {text: "German Law Knowledge", active: true},
        {text: "CockroachDB", active: true},
        {text: result.classification, active: false},
      );
      if (result.evidence && result.evidence.length) {
        const source = result.evidence[0];
        metadata.push({text: `${source.official_identifier} · ${source.provision}`, active: false});
      }
    }
    if (criticalLoop) metadata.push({text: "Critical Prompt Loop · 1+3+1", active: true});
    const finalSpeaker = germanLaw
      ? `${selectedModel ? selectedModel.label : "Gemma"} — Final · ${result.verified ? "VERIFIED" : "LIMITED"}`
      : selectedModel ? selectedModel.label : "Assistant";
    appendMessage("assistant", finalSpeaker, result.answer, metadata);
    setStatus("Response delivered. Ready for operator input.", "neutral");
  } catch (error) {
    appendMessage("error", "Request stopped safely", error.message || "LOCAL_REQUEST_FAILED");
    setStatus(`Stopped safely: ${error.message || "LOCAL_REQUEST_FAILED"}`, "error");
  } finally {
    state.runId = null;
    setBusy(false);
    elements.prompt.focus();
  }
}

async function clearConversation() {
  if (state.busy) return;
  try {
    await api("/api/reset", {method: "POST", body: "{}"});
    elements.history.replaceChildren();
    const empty = document.createElement("div");
    empty.id = "empty-chat";
    empty.className = "empty-chat";
    const title = document.createElement("p");
    title.textContent = "Ask anything.";
    const subtitle = document.createElement("span");
    subtitle.textContent = "Conversation cleared. The two modules remain independently selectable.";
    empty.append(title, subtitle);
    elements.history.append(empty);
    elements.emptyChat = empty;
    setStatus("Conversation cleared.", "neutral");
  } catch (error) {
    setStatus(`Could not clear: ${error.message}`, "error");
  }
}

async function initialize() {
  const status = await api("/api/status");
  state.csrf = status.csrf_token;
  state.models = status.models;
  state.roles = status.observer_roles;
  state.demoPrompt = status.demo_prompt;
  state.models.forEach((model) => elements.model.append(createModelOption(model)));
  elements.model.value = status.default_model_id;
  renderObservers();
  elements.model.disabled = false;
  elements.send.disabled = false;
  setStatus("Ready for operator input.", "neutral");
}

elements.cplToggle.addEventListener("change", renderModeState);
elements.knowledgeToggle.addEventListener("change", renderModeState);
elements.model.addEventListener("change", () => {
  document.querySelectorAll(".observer-model").forEach((select) => {
    select.value = elements.model.value;
  });
});
elements.send.addEventListener("click", sendPrompt);
elements.clear.addEventListener("click", clearConversation);
elements.preset.addEventListener("click", () => {
  elements.prompt.value = state.demoPrompt;
  elements.prompt.focus();
});
elements.prompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendPrompt();
  }
});

initialize().catch((error) => {
  setStatus(`Startup failed: ${error.message || "LOCAL_STARTUP_FAILED"}`, "error");
});
