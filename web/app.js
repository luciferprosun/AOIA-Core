const state = {
  currentModel: "",
};

const elements = {
  modelSelect: document.querySelector("#model-select"),
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
  state.currentModel = status.model;
  elements.currentModelBadge.textContent = status.model;
  elements.sessionModel.textContent = status.model;
  elements.sessionSummary.textContent = status.browser_active
    ? "Browser session is active and ready for follow-up actions."
    : "Browser is idle. Shell and filesystem tools remain available.";
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

function hydrateModelSelect(availableModels, currentModel) {
  const choices = availableModels.map((line) => {
    const [aliasPart, modelPart] = line.split("->").map((item) => item.trim());
    return {
      label: aliasPart,
      value: modelPart,
    };
  });

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
}

async function switchModel() {
  const model = elements.modelSelect.value;
  const payload = await jsonFetch("/api/model", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
  elements.modelNote.textContent = payload.notice || `Model switched to ${payload.model}`;
  applyStatus(payload.status);
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

for (const button of document.querySelectorAll(".quick-action")) {
  button.addEventListener("click", () => {
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

elements.promptInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

async function bootstrap() {
  addMessage(
    "System",
    "App222 web shell is ready. Use the model selector on the left, then send a prompt or a slash command."
  );
  try {
    await refreshStatus();
  } catch (error) {
    addMessage("System", `Startup failed: ${error}`);
  }
}

bootstrap();
