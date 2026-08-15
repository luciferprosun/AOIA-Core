#!/usr/bin/env node
/* Real operator-equivalent browser acceptance for the final recording demo. */

import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const origin = process.env.AIOA_RECORDING_ORIGIN || "http://127.0.0.1:8765";
const noCalls = process.env.AIOA_VALIDATE_NO_CALLS === "1";
const goldenPrompt = "Vervollständige den Satz zur BMJErnAnO: „Diese Anordnung tritt am [Datum] in Kraft.“";
const profile = mkdtempSync(join(tmpdir(), "aioa-final-recording-chrome-"));
const screenshots = {
  knowledge: "/home/l/.cache/aioa-final-knowledge-on.png",
  cpl: "/home/l/.cache/aioa-final-cpl.png",
};
const consoleErrors = [];
const consoleWarnings = [];
let browser;
let sessionId;
let nextId = 1;
const pending = new Map();

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitUntil(check, timeoutMilliseconds, label) {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    const value = await check();
    if (value) return value;
    await sleep(400);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

function connectDebuggerPipe() {
  let buffered = Buffer.alloc(0);
  browser.stdio[4].on("data", (chunk) => {
    buffered = Buffer.concat([buffered, chunk]);
    let separator;
    while ((separator = buffered.indexOf(0)) !== -1) {
      const raw = buffered.subarray(0, separator).toString("utf8");
      buffered = buffered.subarray(separator + 1);
      if (!raw) continue;
      const message = JSON.parse(raw);
      if (message.id && pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message));
        else resolve(message.result || {});
        continue;
      }
      if (message.method === "Runtime.exceptionThrown") {
        consoleErrors.push({
          kind: "runtime-exception",
          text: String(message.params?.exceptionDetails?.text || "exception").slice(0, 200),
        });
      }
      if (message.method === "Log.entryAdded") {
        const entry = message.params?.entry;
        const projection = {
          kind: `browser-${entry?.level || "unknown"}`,
          source: entry?.source,
          text: String(entry?.text || "").slice(0, 200),
        };
        if (entry?.level === "error") consoleErrors.push(projection);
        if (entry?.level === "warning") consoleWarnings.push(projection);
      }
    }
  });
}

function command(method, params = {}, useSession = true) {
  const id = nextId++;
  const payload = { id, method, params };
  if (useSession && sessionId) payload.sessionId = sessionId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    browser.stdio[3].write(JSON.stringify(payload) + "\0");
  });
}

async function evaluate(expression) {
  const response = await command("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (response.exceptionDetails) throw new Error("Browser evaluation failed");
  return response.result?.value;
}

async function setToggle(selector, expected) {
  await evaluate(`(() => {
    const value = document.querySelector(${JSON.stringify(selector)});
    if (!value) return false;
    if (value.checked !== ${JSON.stringify(expected)}) value.click();
    return value.checked;
  })()`);
}

async function resetConversation() {
  await evaluate("document.querySelector('#clear-button').click(); true");
  await waitUntil(
    () => evaluate("Boolean(document.querySelector('#empty-chat'))"),
    10_000,
    "conversation reset",
  );
}

async function insertPrompt(prompt) {
  await evaluate(`(() => {
    const input = document.querySelector('#prompt-input');
    input.focus();
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return document.activeElement === input;
  })()`);
  await command("Input.insertText", { text: prompt });
  const actual = await evaluate("document.querySelector('#prompt-input').value");
  if (actual !== prompt) throw new Error("Browser input did not preserve exact UTF-8 prompt");
}

async function runFlow({ prompt, cpl, knowledge, timeout }) {
  await setToggle("#cpl-toggle", cpl);
  await setToggle("#knowledge-toggle", knowledge);
  if (cpl && knowledge) throw new Error("Acceptance never invokes unavailable State D");
  await evaluate(`(() => {
    const model = document.querySelector('#model-select');
    model.value = 'google/gemma-3-27b-it';
    model.dispatchEvent(new Event('change', { bubbles: true }));
    document.querySelectorAll('.observer-model').forEach((value) => {
      value.value = 'google/gemma-3-27b-it';
      value.dispatchEvent(new Event('change', { bubbles: true }));
    });
    return true;
  })()`);
  await insertPrompt(prompt);
  const priorMessages = await evaluate("document.querySelectorAll('.message.assistant, .message.error').length");
  await evaluate("document.querySelector('#send-button').click(); true");
  await waitUntil(
    async () => {
      const projection = await evaluate(`(() => ({
        terminalMessages: document.querySelectorAll('.message.assistant, .message.error').length,
        sendEnabled: !document.querySelector('#send-button').disabled,
      }))()`);
      return projection.terminalMessages > priorMessages && projection.sendEnabled;
    },
    timeout,
    cpl ? "CPL final response" : knowledge ? "knowledge response" : "direct response",
  );
  return evaluate(`(() => {
    const message = [...document.querySelectorAll('.message.assistant, .message.error')].at(-1);
    return {
      kind: message?.classList.contains('error') ? 'error' : 'assistant',
      answer: message?.querySelector('.message-body')?.textContent.trim() || '',
      metadata: [...(message?.querySelectorAll('.message-meta span') || [])].map((value) => value.textContent.trim()),
      status: document.querySelector('#run-status-text')?.textContent.trim() || '',
      observers: [...document.querySelectorAll('.observer-card')].map((card) => ({
        role: card.querySelector('.observer-role')?.textContent.trim() || '',
        state: card.querySelector('.observer-state')?.textContent.trim() || '',
        summary: card.querySelector('.observer-summary')?.textContent.trim() || '',
      })),
    };
  })()`);
}

async function accounting() {
  return evaluate("fetch('/api/status').then((response) => response.json()).then((value) => value.accounting)");
}

async function screenshot(path) {
  await sleep(250);
  const capture = await command("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
  });
  writeFileSync(path, Buffer.from(capture.data, "base64"));
}

try {
  browser = spawn(
    "/usr/bin/google-chrome",
    [
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      "--remote-debugging-pipe",
      `--user-data-dir=${profile}`,
      "about:blank",
    ],
    { stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"] },
  );
  connectDebuggerPipe();
  const created = await command("Target.createTarget", { url: "about:blank" }, false);
  const attached = await command(
    "Target.attachToTarget",
    { targetId: created.targetId, flatten: true },
    false,
  );
  sessionId = attached.sessionId;
  await command("Runtime.enable");
  await command("Log.enable");
  await command("Page.enable");
  await command("Page.bringToFront");
  await command("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await command("Page.navigate", { url: origin });
  await waitUntil(
    () => evaluate("document.readyState === 'complete' && !document.querySelector('#model-select').disabled"),
    30_000,
    "recording UI readiness",
  );

  const initial = await evaluate(`(() => ({
    model: document.querySelector('#model-select').value,
    models: [...document.querySelectorAll('#model-select option')].map((value) => value.value),
    cplOff: !document.querySelector('#cpl-toggle').checked,
    knowledgeOff: !document.querySelector('#knowledge-toggle').checked,
    cplHidden: document.querySelector('#cpl-panel').hidden,
    textarea: Boolean(document.querySelector('#prompt-input')),
    send: Boolean(document.querySelector('#send-button')),
    forbidden: ['OPENROUTER_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'postgresql://', 'cockroachdb://']
      .some((value) => document.documentElement.innerHTML.includes(value)),
  }))()`);
  if (
    initial.model !== "google/gemma-3-27b-it" ||
    !initial.models.includes("google/gemma-3-27b-it") ||
    !initial.cplOff || !initial.knowledgeOff || !initial.cplHidden ||
    !initial.textarea || !initial.send || initial.forbidden
  ) throw new Error("Initial browser contract failed");

  await setToggle("#cpl-toggle", true);
  const observerPreview = await evaluate(`(() => ({
    visible: !document.querySelector('#cpl-panel').hidden,
    roles: [...document.querySelectorAll('.observer-role')].map((value) => value.textContent.replace('Role: ', '').trim()),
    slots: document.querySelectorAll('.observer-card').length,
  }))()`);
  if (
    !observerPreview.visible ||
    observerPreview.slots !== 3 ||
    observerPreview.roles.join("|") !== "Logic & Claims|Safety & Authority|Evidence & Consistency"
  ) throw new Error("Historical observer preview failed");
  await setToggle("#cpl-toggle", false);

  if (noCalls) {
    await sleep(1_500);
    const finalAccounting = await accounting();
    if (consoleErrors.length) {
      throw new Error(`Browser console errors: ${JSON.stringify(consoleErrors)}`);
    }
    console.log(JSON.stringify({
      status: "PASS_NO_CALLS",
      initial,
      observerPreview,
      accounting: finalAccounting,
      browserConsoleErrors: consoleErrors.length,
      browserConsoleWarnings: consoleWarnings.length,
      warnings: consoleWarnings,
    }));
  } else {
  await resetConversation();
  const test1 = await runFlow({
    prompt: "Reply with exactly: AIOA_DEMO_OK",
    cpl: false,
    knowledge: false,
    timeout: 180_000,
  });
  if (test1.kind !== "assistant" || test1.answer !== "AIOA_DEMO_OK") {
    throw new Error("TEST 1 base Gemma chat failed");
  }

  await resetConversation();
  const test2 = await runFlow({
    prompt: goldenPrompt,
    cpl: false,
    knowledge: false,
    timeout: 180_000,
  });
  if (test2.kind !== "assistant" || !test2.answer) throw new Error("TEST 2 knowledge OFF failed");

  await resetConversation();
  const test3 = await runFlow({
    prompt: goldenPrompt,
    cpl: false,
    knowledge: true,
    timeout: 240_000,
  });
  if (
    test3.kind !== "assistant" ||
    !test3.answer ||
    !test3.metadata.includes("CockroachDB") ||
    !test3.metadata.includes("EVIDENCE_ASSISTED_NOT_VERIFIED") ||
    !test3.metadata.some((value) => value.includes("BJNR1330A0023") && value.includes("III."))
  ) throw new Error("TEST 3 CockroachDB knowledge path failed");
  await screenshot(screenshots.knowledge);

  await resetConversation();
  const test4 = await runFlow({
    prompt: "Reply briefly: What is 2 + 2?",
    cpl: true,
    knowledge: false,
    timeout: 420_000,
  });
  if (
    test4.kind !== "assistant" ||
    !test4.answer ||
    test4.observers.length !== 3 ||
    test4.observers.some((value) => value.state !== "COMPLETED")
  ) throw new Error("TEST 4 historical CPL failed");
  await screenshot(screenshots.cpl);

  const finalAccounting = await accounting();
  if (finalAccounting.direct_completed !== 4 || finalAccounting.cpl_completed !== 5) {
    throw new Error(`Provider accounting mismatch: ${JSON.stringify(finalAccounting)}`);
  }
  if (consoleErrors.length) {
    throw new Error(`Browser console errors: ${JSON.stringify(consoleErrors)}`);
  }
  console.log(JSON.stringify({
    status: "PASS",
    initial,
    observerPreview,
    test1,
    test2,
    test3,
    test4,
    sameGermanLawPrompt: true,
    accounting: finalAccounting,
    browserConsoleErrors: consoleErrors.length,
    browserConsoleWarnings: consoleWarnings.length,
    warnings: consoleWarnings,
    screenshots,
  }));
  }
} finally {
  if (browser && browser.exitCode === null) {
    browser.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => browser.once("exit", resolve)),
      sleep(5_000),
    ]);
  }
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
}
