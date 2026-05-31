# AOIA-Core

AOIA-Core is a local-first runtime for AI-assisted engineering workflows with explicit evidence, provenance, and model-output boundaries. It separates evidence, provenance, contradictions, logs, memory traces, and runtime state from raw model output.

Grant reviewers: start with [Quick Start for Grant Reviewers](docs/reviewer/QUICK_START_FOR_GRANT_REVIEWERS.md) and [AOIA/NMS Reviewer Glossary](docs/nms/GLOSSARY.md).

AOIA-Core exists because AI-assisted workflows often blur the line between what a model said, what a tool produced, what was logged, and what can actually be trusted or replayed. AOIA-Core makes those layers explicit.

## What AOIA-Core Controls

- evidence boundaries
- provenance verification
- contradiction tracking
- retrieval boundaries
- runtime state
- deterministic operator workflows
- human-approved execution

## What AOIA-Core Is Not

- not a chatbot
- not a generic AI agent
- not a truth engine
- not a RAG wrapper
- not GUI-first
- not cloud-first
- not a self-modifying/autonomous swarm

## Project Layers

1. AOIA-Core: the final practical engineering project and main repository deliverable.
2. MHLM / MDLH: AI-safety research background about multi-model hallucination, recursive consensus, and provenance drift.
3. LSC: scientific case-study background and stress-test context, not the core deliverable of AOIA-Core.

## Current Technical Status

- GT6 authority audit complete
- GT6B full manifest complete
- GT7 cleanup complete through Batch 3
- latest confirmed HEAD: `fd74671`
- validation at public-entry savepoint: `145` tests run, `4` skipped
- see [Implemented Capabilities](docs/governance/IMPLEMENTED_CAPABILITIES.md) for a conservative status table separating implemented, partial, planned, and documentation-only items.

## For External Reviewers

Start here:

- [Project Overview for Reviewers](docs/reviewer/PROJECT_OVERVIEW_FOR_REVIEWERS.md)
- [Implemented Capabilities](docs/governance/IMPLEMENTED_CAPABILITIES.md)
- [One Concrete Example](docs/reviewer/ONE_CONCRETE_EXAMPLE.md)
- [External Model Output Policy](docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md)
- [Stress-Test Documentation](docs/stress_tests/README.md)

AOIA-Core should be read as a local-first boundary-enforcement runtime for AI-assisted engineering workflows. It is not AGI, not autonomous, not a truth engine, not validated science, and not production-ready.

Evidence Memory Phase 1A is not active unless explicitly approved later through ADR/operator decision.

## License

AOIA-Core is released under the MIT License. See [LICENSE](LICENSE).

If future documentation-specific licensing is desired, it can be clarified later.

## External Model Output Policy

AOIA-Core preserves some model-assisted reviews, forensic exports, and audit packets as historical context. These files are not canonical source, not evidence, and not runtime authority. They must not be ingested into Evidence Memory or used to override governance contracts or ADRs. See [docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md](docs/governance/EXTERNAL_MODEL_OUTPUT_POLICY.md).

## Reviewer / Stress-Test Documentation

AOIA-Core GT8 includes additional documentation to aid reviewers. See:

- [docs/stress_tests/README.md](docs/stress_tests/README.md)
- [docs/stress_tests/AOIA_NMS_STRESS_TEST_PROTOCOL.md](docs/stress_tests/AOIA_NMS_STRESS_TEST_PROTOCOL.md)
- [docs/stress_tests/FAILURE_MODES.md](docs/stress_tests/FAILURE_MODES.md)
- [docs/stress_tests/LSC_CASE_STUDY_PROTOCOL.md](docs/stress_tests/LSC_CASE_STUDY_PROTOCOL.md)
- [docs/stress_tests/MODEL_AUDIT_MATRIX.md](docs/stress_tests/MODEL_AUDIT_MATRIX.md)
- [docs/ROADMAP_4_MONTHS.md](docs/ROADMAP_4_MONTHS.md)

These documents formalize the reviewer credibility pass for GT8. They clarify that stress-test contexts and scientific case studies are not part of the AOIA-Core deliverable.

## Existing Runtime Notes

This repository publishes the functional project code and architecture work
without private API secrets, browser state, local session memory, or machine-
specific runtime artifacts.

## AOIA

AOIA stands for Adaptive Oceanic Intelligence Architecture.

In this repository, AOIA is used narrowly:

- deterministic routing
- local-first execution
- token and energy conservation
- biologically inspired scheduling research

It is not an AGI system, autonomous swarm, or self-modifying runtime.

## Runtime architecture

```text
USER
  -> Local router first
  -> Aureon provider
  -> Gemini provider when selected
  -> fallback API providers
  -> JSON action
  -> executor
  -> shell / filesystem / browser tools
  -> result
  -> next action or final response
```

The runtime can:

- execute shell commands
- create and edit files
- keep lightweight agent state
- launch and reuse a persistent Playwright browser session
- inspect live webpages
- capture screenshots
- switch models from inside the app with `/model`

## AOIA and DVM references

The repository contains current AOIA foundation work and related background references. The AOIA name draws on biological layering concepts as historical routing inspiration. This background is not part of the AOIA-Core runtime authority or reviewer deliverable.

## Application catalog

The repository also contains sibling application directories under `apps/`.

The `apps/` directory may contain sibling or imported application material and should not be treated as the AOIA-Core runtime deliverable unless explicitly documented.

Current imported subproject:

- `apps/flameborn-academy-codex-sparrow/`
  - `flAmeBornLLC / LLM Academy`
  - package identifier: `codexprosparrow`

## Project structure

```text
flAmeBorbLLC-AIOA-LiGaLu/
├── main.py
├── requirements.txt
├── run.sh
├── prompts/
│   └── system_prompt.txt
├── tools/
│   ├── browser_tools.py
│   ├── executor.py
│   ├── filesystem_tools.py
│   ├── memory.py
│   ├── shell_tools.py
│   ├── system_info.py
│   └── validator.py
├── adaptive_routing/
├── docs/
├── knowledge/
├── orchestrator/
├── providers/
├── router/
├── state/
└── tests/
```

Private runtime directories such as local logs, browser profile data, session
memory, checkpoints, and virtual environments are intentionally not published.

## Setup

### 1. API key

Set one of:

- `AUREON_API_BASE_URL` and `AUREON_API_KEY` for a live Aureon-compatible endpoint
- `OPENROUTER_API_KEY` for OpenRouter fallback
- `GEMINI_API_KEY` if you want to switch to Gemini with `/model gemini`

Inside the CLI:

- `/model` shows the current model and presets
- `/model aureon` switches to the local-first Aureon preset
- `/model gemini` switches to Gemini
- `/model provider/model` accepts explicit provider and model names

### 2. Runtime bootstrap

`run.sh` now bootstraps `.venv` automatically if it does not exist:

```bash
cd /path/to/flAmeBorbLLC-AIOA-LiGaLu
./run.sh
```

If `.venv` is missing, `run.sh` now falls back to system `python3` so the runtime can still start on a low-spec machine without pulling new packages first.

### 2b. Web UI

The project now also ships with a local web shell that keeps the same runtime
and model switching logic but presents it through a Codex-style interface.

```bash
cd /path/to/flAmeBorbLLC-AIOA-LiGaLu
./run_web.sh
```

Default URL:

```text
http://127.0.0.1:4311
```

### 2c. Terminal operator console

The minimal Textual TUI wraps the existing runtime without replacing routing,
provider, provenance, retrieval, or approval semantics.

```bash
cd /path/to/flAmeBorbLLC-AIOA-LiGaLu
./scripts/start_tui.sh
```

Controls:

- Enter a normal request to run it through `AgentRuntime.run_text_request()`.
- `/model` lists configured model presets.
- `/model gemini`, `/model openrouter`, `/model deepseek`, or `/model aureon` uses the existing provider switch path.
- `/status` prints the current runtime status into the transcript.
- `/clear` clears the visible transcript.
- `Ctrl+A` approves a pending risky action.
- `Ctrl+X` rejects a pending risky action.
- `Ctrl+P` / `Ctrl+N` navigate command history.
- `Ctrl+R` refreshes runtime status.
- `Ctrl+C` or `q` exits.

The TUI shows only operator-visible transcript output and replay-safe
operational telemetry. It intentionally does not display hidden reasoning,
raw provider internals, prompts, or chain-of-thought traces.

### 3. Playwright

Required Python dependency:

```bash
pip install -r requirements.txt
```

Browser binaries:

```bash
source .venv/bin/activate
playwright install
```

## Deterministic knowledge pipeline

The project includes a static RHCSA knowledge workflow:

- raw PDF extraction
- section parsing
- canonical command generation
- deterministic keyword index
- deterministic context pack generation
- static context injection

Artifacts live under `knowledge/`.

## JSON actions

The model must return one JSON object per step.

Examples:

```json
{
  "action": "shell_execute",
  "command": "curl --version",
  "reason": "Check curl availability.",
  "requires_confirmation": false
}
```

```json
{
  "action": "write_file",
  "path": "/home/l/Desktop/AI_TEST/note.txt",
  "content": "hello",
  "reason": "Write a text file safely."
}
```

```json
{
  "action": "browser_open",
  "url": "https://www.google.com",
  "reason": "Open Google in the persistent local browser."
}
```

## Tool capabilities

### Shell

- `shell_execute`
- supports quoted strings, pipes, redirects, `&&`, `;`
- confirmations for `sudo`, `apt install`, `pip install`, `npm install`

### Filesystem

- `create_folder`
- `create_file`
- `write_file`
- `append_file`
- `read_file`
- `move_file`
- `delete_file`
- `search_in_project`

### Browser

- `browser_start`
- `browser_open`
- `browser_click`
- `browser_type`
- `browser_press`
- `browser_read_html`
- `browser_get_visible_text`
- `browser_screenshot`
- `browser_current_url`
- `browser_close`

Browser state is persistent for the lifetime of the runtime process.

## Local URL bootstrap

Requests that already contain a URL now avoid wasting model quota on trivial
browser setup. The runtime can locally:
- unwrap common redirect links such as `l.facebook.com/...?...u=<target>`
- start the browser
- open the target URL
- capture visible page text before the first model step

This means the model is used for interpretation, not for obvious setup work.

## Memory and state

The runtime remembers:
- current working directory
- current task
- previous commands
- recent outputs
- current browser page
- open tabs
- screenshots
- Obsidian vault notes in `obsidian_vault/`

Stored runtime state is local and intentionally excluded from the public repo.

## Orchestration MVP

The runtime is now structured as a small AI-agent orchestration layer rather
than an offline chatbot wrapper.

Current layers:
- Planner: asks the active cloud model for a short JSON plan before falling back to single-step action mode.
- Model router: tries the configured fallback chain in `state/providers.json`.
- Provider support: Gemini, OpenRouter, DeepSeek-compatible API, HuggingFace, and live Aureon endpoints.
- Command proposal: models return structured actions only; they do not execute directly.
- Human approval: every non-`respond` action requires ENTER approval before execution.
- Executor: runs approved shell, filesystem, browser, and project scan actions.
- Memory hats: modular context overlays stored in `memory/hats/`.
- Project scanner: `/scan PATH` maps files, entrypoints, file types, and writes `project_scan.json`.
- Logging: actions, results, sessions, errors, and vault notes remain persistent.

Useful commands:

```bash
/setup
/providers
/hat list
/hat load coding
/scan /path/to/project
```

Provider configuration:
- `state/providers.json` controls fallback order.
- API keys are loaded from standard `~/.config/*/api.env` files and the known USB FlameBorn `.env` offload.
- There is no fake offline model response. If all cloud providers fail, the runtime reports the real provider errors.

## Safety model

Blocked patterns include:
- `rm -rf /`
- fork bombs
- dangerous `chmod` / `chown` on system paths
- `curl | bash`
- command substitution and heredocs

Human approval is required for every non-final action. Press ENTER to approve
or type `n`, `no`, `cancel`, `reject`, or `stop` to reject.

## Tests

Run:

```bash
cd /home/l/APP2/codex_clone
. .venv/bin/activate
python -m unittest discover -s tests -v
```

Covered:
1. create folder on desktop
2. create txt file inside folder
3. write content into txt file
4. install-command confirmation path
5. run `curl --version`
6. browser open
7. browser search interaction on local page
8. screenshot capture
9. visible text extraction
10. page navigation

## Live browser notes

Real public websites may still present anti-bot or consent pages.

Observed during smoke tests:
- opening `https://www.google.com` works
- screenshots and visible text extraction work on live pages
- direct Google search URLs may trigger `sorry` anti-bot pages depending on IP and traffic history
- facebook redirect links can be unwrapped locally to their real target URLs

That is a site-side constraint, not a local executor failure.
