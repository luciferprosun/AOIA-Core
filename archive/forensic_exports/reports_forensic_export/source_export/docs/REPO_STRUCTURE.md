# Repository Structure

## Top-Level Layout

```text
app2terminl_opened/
  main.py
  webapp.py
  run.sh
  run_web.sh
  requirements.txt
  README.md
  adaptive_routing/
  commands/
  docs/
  knowledge/
  memory/
  obsidian_vault/
  orchestrator/
  prompts/
  providers/
  reports/
  router/
  state/
  tests/
  tools/
  web/
```

## Runtime Areas

`main.py`
- Owns the CLI runtime loop.
- Coordinates prompt construction, local routing, model calls, execution, and
  memory updates.

`webapp.py`
- Exposes a local HTTP UI wrapper around the same runtime.
- Must remain secondary to the terminal runtime.

`commands/`
- Slash command and local command registry.

`tools/`
- Local execution tools: shell, filesystem, browser, memory, validation, project
  scanning, and web reading.

`providers/`
- Provider adapters and model configuration.
- AOIA must not directly alter provider behavior until a later integration step.

`orchestrator/`
- Existing orchestration helpers.
- New adaptive routing layers should stay outside this directory until the
  contract is stable.

`knowledge/`
- Local operational knowledge engines.
- Currently includes RHCSA/Linux retrieval.

`memory/`
- Runtime memory and memory-hat helpers.

`state/`
- Local runtime state.
- Do not commit or publish secrets, browser profiles, or private state.

`web/`
- Static local web interface.

## AOIA Areas

`adaptive_routing/`
- Isolated AOIA foundation.
- Current status: documentation and static prototypes only.
- No backend integration yet.

`adaptive_routing/environment/`
- Static environmental profiles.
- Current status: local data and simple classifier only.

`docs/`
- Repository constitution, architecture notes, glossary, constraints, and ADRs.

`docs/adr/`
- Architecture Decision Records.
- One decision per file.

## Checkpoints

`checkpoints/`
- Local restore points.
- Checkpoints should describe scope and excluded generated files.

