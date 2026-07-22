# AOIA Control Chat — Competition Demo

A lightweight desktop chat application demonstrating AOIA-Core's
human-controlled, epistemic-control concept: provider output is never
authority, knowledge retrieval is evidence only, and this application
executes no actions of any kind.

This demo is a **separate track** from the AOIA-Core production runtime.
It is not the production-safe agent, and it does not weaken or bypass any
of AOIA-Core's authority boundaries.

## What this demo shows

- A real, functional multi-turn chat session against OpenRouter, with
  live model selection (remote catalog or a manual model ID).
- An optional, read-only "Linux / UNIX Knowledge" evidence profile,
  backed by the AOIA-Core repository's existing local RHCSA/Linux
  knowledge index — attached only when you explicitly select it.
- A visible epistemic-control status strip and a per-answer
  "AI-generated suggestion — not authority" label.
- A safe **Offline UI Demo** mode that shows the interface with a
  deterministic canned reply and contacts no model at all.

## What this demo deliberately cannot do

- It cannot run shell commands, Git commands, browser automation, or
  package installs.
- It cannot write, patch, commit, or push anything.
- It cannot call tools or execute code proposed by a model.
- It never retries a failed request automatically and never silently
  falls back to a different provider or model.
- It never stores your API key on disk by default, never logs it, and
  never includes it in an error message.
- A selected knowledge profile is evidence only — it is never treated as
  authority, and retrieved text is never executed as instructions.

## System requirements

- Python 3.12 (matches the AOIA-Core repository's own `requires-python`).
- Tkinter for your Python installation (the `tkinter` standard-library
  module). On Debian/Ubuntu/Linux Mint this is the `python3-tk` package.
  This demo will **not** install it automatically — if it's missing, the
  launcher and the app both print a clear message telling you the exact
  package to install yourself.
- No other third-party dependency is required to run the application
  (`urllib`/`tkinter`/`json` from the standard library only).

## Launching

```bash
./run_aoia_demo.sh
```

or, equivalently, from the repository root:

```bash
python3 -m apps.aoia_desktop_demo
```

## Entering an OpenRouter API key

1. Open **Settings** (top bar).
2. Paste your key into **API Key** (masked by default; use **Show key**
   to reveal it while typing).
3. Click **Use for this session** — the key is now held in memory only,
   for this run of the application. It is never written to
   `~/.config/aoia-control-chat-demo/config.json`.
4. Optionally click **Test connection** to confirm it works before
   chatting.

If your OS has a secure keyring available in a future revision of this
demo, an explicit opt-in persistent-storage option may be offered — as
shipped, storage is session-only.

## Refreshing and selecting a model

- In the left panel, click **Refresh Models** to pull the current
  OpenRouter catalog (requires a working API key). The dropdown shows
  each model's name and ID.
- Alternatively, open **Settings** and type a model slug directly into
  **Manual Model ID** — this always takes precedence over the dropdown
  selection if both are set.
- The app never silently substitutes a different model if your choice
  fails; you'll see the error instead.

## Model Only mode

Leave **Knowledge Profile** set to **None** (the default). The status
panel will read `Knowledge: None`, and the model answers purely from
conversation context.

## Attaching Linux/UNIX knowledge

1. In the left panel, choose **Linux / UNIX Knowledge** from the
   **Knowledge Profile** dropdown.
2. Ask a Linux/RHCSA-flavored question (e.g. "how do I check disk
   usage", "explain a systemd unit file").
3. If the local index has a confident match, an **Evidence** panel on
   the right lists the retrieved source(s), and the reply carries a
   "Sources attached — inspect evidence before relying on the answer"
   label. If there isn't a confident match, no evidence is attached and
   the model answers from conversation context alone — this demo never
   invents a citation.

## Offline UI Demo mode

Check **Offline UI Demo** in the left panel. Every send now returns a
fixed, clearly labeled sample line and contacts no provider at all. This
is for showing the interface (e.g. on a machine with no network) — it
is never used as a silent fallback when a real request fails.

## Manual smoke test against the real OpenRouter API

`scripts/manual_smoke_test_openrouter.py` makes exactly one small, real
request. It never runs automatically — only when you set
`OPENROUTER_API_KEY` and invoke it yourself:

```bash
OPENROUTER_API_KEY=sk-... python3 scripts/manual_smoke_test_openrouter.py
```

## Clearing settings

Open **Settings** and use **Clear key** to drop the in-memory API key.
To remove the saved non-secret preferences file entirely, delete
`~/.config/aoia-control-chat-demo/config.json` (this file never contains
your API key).

## Security and privacy notes

- The API key is entered manually and lives only in memory for the
  lifetime of the running process.
- Non-secret preferences (selected provider/model, window size,
  timeout, selected knowledge profile) are stored at
  `~/.config/aoia-control-chat-demo/config.json`.
- Requests are non-streaming (`stream: false`), single-attempt, with a
  bounded timeout and a bounded response size. There is no automatic
  retry and no automatic provider fallback.
- Errors shown in the UI are redacted before display; expandable
  technical detail is also redacted.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ERROR: tkinter is not available...` | Install your distribution's Tkinter package (e.g. `sudo apt install python3-tk`) yourself, then re-run. |
| "No API key set for this session" | Open Settings, enter a key, click **Use for this session** (or set `OPENROUTER_API_KEY`). |
| "Connection failed: OpenRouter HTTP 401 ..." | The key is invalid or missing scopes; verify it on openrouter.ai. |
| "Connection failed: OpenRouter HTTP 402/429 ..." | Insufficient credits or rate-limited; check your OpenRouter account. |
| Refresh Models returns nothing | Confirm the key works via **Test connection** first. |
| No evidence ever appears for Linux/UNIX Knowledge | The local read-only index only answers confidently matched, in-scope Linux/RHCSA queries by design — it explicitly refuses low-confidence matches rather than guessing. |

## Competition demo flow (about three minutes)

1. Launch AOIA Control Chat (`./run_aoia_demo.sh`).
2. Open **Settings**.
3. Enter your OpenRouter API key.
4. Click **Test connection**.
5. Click **Refresh Models**.
6. Choose a model from the dropdown (or type one manually).
7. Ask a normal question with **Knowledge Profile: None** (Model Only mode).
8. Select **Linux / UNIX Knowledge** from the Knowledge Profile dropdown.
9. Ask a source-specific Linux/RHCSA question.
10. Point at the **Evidence** panel showing the attached source(s).
11. Call out the status strip and the per-answer label:
    - "AI-generated suggestion — not authority"
    - "Knowledge: Evidence only"
    - "Actions: Disabled"
    - "Human control: Required"

This flow is documentation only — it is not hardcoded into the
application's runtime behavior.

## Relationship to the AOIA-Core production runtime

This demo is a standalone, isolated application built inside a **clone**
of the AOIA-Core repository, on its own local branch
(`demo/openai-competition-desktop-1a`). It does not import the
production runtime's provider-gateway, execution, patch, Git, browser,
or package-installation modules. It reuses only the repository's
existing **read-only** Linux/RHCSA retrieval facade
(`runtime/retrieval/facade.py`) to source evidence — nothing here writes
to, rebuilds, or otherwise mutates that index.
