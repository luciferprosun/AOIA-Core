# Memory Split Plan

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: `runtime/tools/memory.py` and direct dependency surface

## Purpose

This document maps the current `memory.py` contamination structure before any implementation work begins. It does not authorize a runtime refactor, module move, adapter extraction, provider change, routing change, or governance implementation.

Phase 1A froze the AOIA memory ontology:
- L0 Ephemeral Runtime State
- L1 Operational Logs
- L2 Reasoning Traces
- L3 Provenance Records
- L4 Immutable Evidence
- L5 Contradiction Registry

Phase 1B maps how the current runtime violates, approximates, or bypasses those layers.

## Current MemoryStore Responsibilities

`runtime/tools/memory.py` currently owns all of the following in one module:

- Runtime path creation: `build_runtime_paths()` creates `state/`, `memory/`, `screenshots/`, and `logs/**`.
- Vault path creation: `build_obsidian_vault_paths()` creates `obsidian_vault/**` and initial vault config.
- L0 state object: `AgentMemory` stores `cwd`, `current_task`, command history, recent outputs, browser state, and screenshots.
- L0 persistence: `MemoryStore.save()` serializes `AgentMemory` into `state/agent_state.json`.
- L1 history: `append_history()` appends JSONL records to `memory/history.jsonl`.
- L1 browser log: `append_browser_event()` appends JSONL records to `logs/browser/browser_<session>.jsonl`.
- L2 reasoning trace: `append_reasoning()` appends JSONL records to `memory/reasoning_trace.jsonl`.
- Evidence-like store: `append_evidence()` appends JSONL records to `memory/evidence_memory.jsonl`.
- Vault projection: `append_vault_note()` and `_append_channel_note()` convert live runtime events into human-readable Obsidian notes.

The module is therefore not a memory layer. It is a transitional compound adapter for state, logs, reasoning, evidence-like events, browser events, and human-facing projection.

## Current Write Paths

`MemoryStore.__init__()`:
- Creates mutable runtime directories and vault directories.
- Writes `state/agent_state.json` through `save()`.
- Writes a `session_start` vault note through `append_vault_note()`.
- Risk: runtime startup mutates source-root state before any user action.

`MemoryStore.save()`:
- Writes L0 state to `state/agent_state.json`.
- Risk: volatile runtime state persists inside the repository working tree.

`MemoryStore.append_history()`:
- Writes a JSONL event to `memory/history.jsonl`.
- Also writes a vault daily note and session JSONL record.
- Risk: L1 operational events are immediately projected into human-readable continuity notes.

`MemoryStore.append_evidence()`:
- Writes to `memory/evidence_memory.jsonl`.
- Also writes to `obsidian_vault/Evidence/<session>.md`.
- Risk: accepts arbitrary `kind` and `payload` with no evidence schema, fingerprint, provenance link, or promotion policy.

`MemoryStore.append_reasoning()`:
- Writes to `memory/reasoning_trace.jsonl`.
- Also writes to `obsidian_vault/Reasoning/<session>.md`.
- Risk: generated reasoning is projected as durable human-readable notes.

`MemoryStore.append_browser_event()`:
- Writes to `logs/browser/browser_<session>.jsonl`.
- Also writes a vault note through `append_vault_note("browser_event", payload)`.
- Risk: browser operations become daily continuity notes without evidence capture rules.

`MemoryStore.record_command()`:
- Mutates `AgentMemory.previous_commands`.
- Writes L0 state through `save()`.
- Risk: command history is prompt-visible runtime state and can bias planning.

`MemoryStore.record_result()`:
- Mutates `AgentMemory.recent_outputs`, browser page, open tabs, browser flag, and screenshots.
- Writes L0 state through `save()`.
- Risk: compacted tool output becomes prompt-visible runtime state.

`MemoryStore.append_vault_note()`:
- Writes `obsidian_vault/Daily/<date>.md`.
- Writes `obsidian_vault/Sessions/<session>.jsonl`.
- Risk: vault becomes a mixed projection of L0/L1/browser/session events.

`MemoryStore._append_channel_note()`:
- Writes evidence and reasoning projection notes.
- Risk: a projection channel can look like a canonical memory channel.

## Current Read Paths

Direct runtime reads:
- `AgentRuntime.build_model_request()` reads `memory_store.memory` and injects L0 runtime state into planner prompts.
- `AgentRuntime.snapshot_status()` reads `memory_store.memory`, `vault_dir`, and path metadata.
- Slash command `/vault` reads `runtime.memory_store.vault_dir`.
- `ExecutionEngine.__init__()` reads `memory_store.memory.cwd` and memory paths.

Internal read-before-write paths:
- `append_vault_note()` reads existing daily note text before appending.
- `_append_channel_note()` reads existing channel note text before appending.

No current code path was found that retrieves answer source material from:
- `memory/history.jsonl`
- `memory/reasoning_trace.jsonl`
- `memory/evidence_memory.jsonl`
- `obsidian_vault/**`

This is good for Phase 1A retrieval quarantine, but it is not enforced by a guard.

## Persistence Paths By Layer

L0 current paths:
- `state/agent_state.json`
- in-memory `AgentMemory`

L1 current paths:
- `memory/history.jsonl`
- `logs/browser/browser_<session>.jsonl`
- `logs/sessions/session_<session>.jsonl`
- `logs/commands/<timestamp>.json`
- `logs/errors/error_<timestamp>.json`

L2 current paths:
- `memory/reasoning_trace.jsonl`
- `obsidian_vault/Reasoning/<session>.md`

Pseudo-L4 current paths:
- `memory/evidence_memory.jsonl`
- `obsidian_vault/Evidence/<session>.md`

Projection current paths:
- `obsidian_vault/Daily/<date>.md`
- `obsidian_vault/Sessions/<session>.jsonl`
- `obsidian_vault/Evidence/<session>.md`
- `obsidian_vault/Reasoning/<session>.md`
- `obsidian_vault/.obsidian/app.json`
- `obsidian_vault/00_START_HERE.md`

L3 current paths outside `memory.py`:
- `runtime/provenance_registry.json`
- generated by `runtime/tools/epistemic_registry.py`

L5 current paths outside `memory.py`:
- `runtime/contradiction_registry.json`
- generated by `runtime/tools/epistemic_registry.py`

## Current State Mutation Paths

`set_current_task()`:
- Mutates `AgentMemory.current_task`.
- Writes `state/agent_state.json`.

`update_cwd()`:
- Mutates `AgentMemory.cwd`.
- Writes `state/agent_state.json`.

`record_command()`:
- Appends and truncates `previous_commands` to the last 20.
- Writes `state/agent_state.json`.

`record_result()`:
- Appends and truncates `recent_outputs` to the last 20.
- Updates browser fields from result payloads.
- Appends and truncates screenshots to the last 20.
- Writes `state/agent_state.json`.

These are valid L0 operations only if they remain continuity state. They become doctrine violations when used as source authority, evidence, provenance, or retrieval input.

## Evidence-Related Flows

Executor action result flow:
- `ExecutionEngine._record_execution()` writes a command log JSON file.
- It calls `record_result(result)`.
- It calls `append_history("action_result", payload)`.
- It calls `append_evidence("action_result", payload)`.

This is the clearest Phase 1A violation. Every tool result, rejected approval, shell output, browser event, and filesystem action can be recorded as evidence-like memory without external provenance.

AOIA kernel evidence flow:
- `AOIAEpistemicKernel.evaluate()` retrieves knowledge artifacts and enriches them with provenance and contradiction references.
- `AgentRuntime.handle_knowledge_route()` logs kernel reasoning.
- If evidence exists, it calls `append_evidence("aoia_kernel_evidence", ...)` with query, route, confidence, manual-review flag, and artifact paths.

This flow is closer to the doctrine because it starts from L3-backed knowledge artifacts. It is still incomplete because the `append_evidence()` destination does not enforce L4 immutability, fingerprints, source linkage, schema, or content addressing.

## Reasoning-Trace Flows

Planner flow:
- `create_plan()` writes `planner_request` through `log_reasoning_trace()`.
- `log_reasoning_trace()` delegates to `append_reasoning()`.

Knowledge flow:
- `handle_knowledge_route()` writes `aoia_kernel_decision` reasoning.
- `emit_epistemic_unknown()` writes `unknown_response` reasoning twice in the current flow: once through `log_reasoning_trace()` and once directly through `append_reasoning()`.

Safeguard flow:
- `log_reasoning_trace()` checks `reasoning_trace_enabled`.
- Direct calls to `append_reasoning()` bypass that helper-level gate.

No current retrieval path was found reading L2 as source material. However, L2 is persisted in repo-root runtime outputs and projected into the vault, so quarantine is conceptual rather than enforced.

## Obsidian/Vault Projection Flows

Vault startup:
- `build_obsidian_vault_paths()` creates the full vault layout.
- It writes `.obsidian/app.json` and `00_START_HERE.md` if missing.

Daily/session projection:
- `append_history()` and `append_browser_event()` call `append_vault_note()`.
- `append_vault_note()` writes both daily markdown and session JSONL.
- The vault block contains current `cwd`, current `task`, and a summary extracted from `message`, `summary`, or `error`.

Evidence/reasoning projection:
- `append_evidence()` writes to `obsidian_vault/Evidence/<session>.md`.
- `append_reasoning()` writes to `obsidian_vault/Reasoning/<session>.md`.

Risk:
- Vault notes are derivative projections, but current naming and placement make them look like memory authority.
- Daily notes mix startup events, action results, browser events, and task/cwd context.
- Projection can recursively influence operators, future prompts, or manual copy/paste into knowledge material.

## Runtime Coupling Points

`AgentRuntime.__init__()`:
- Constructs `MemoryStore`.
- Constructs `ExecutionEngine` with the same store.
- Constructs `KnowledgeRouter` and `AOIAEpistemicKernel` separately.
- Creates session log path from `memory_store.paths`.

`AgentRuntime.build_model_request()`:
- Injects L0 runtime state into the model prompt.
- Includes `previous_commands`, `recent_outputs`, browser state, screenshots, active memory hat, `rhcsa_context`, vault path, and tool names.

`ExecutionEngine.__init__()`:
- Uses memory paths for browser profile and screenshots.
- Uses memory command log directory.
- Reads initial cwd from `memory_store.memory`.

`KnowledgeRouter.__init__()`:
- Writes token savings report under `state/`.
- This is not owned by `memory.py`, but it uses the same mutable runtime state area.

## Current Doctrine Violations

Violation 1: L1 becomes pseudo-L4.
- `executor._record_execution()` records every `action_result` as both history and evidence.

Violation 2: L4 destination has no evidence contract.
- `append_evidence()` accepts arbitrary payloads with no fingerprint, source identity, CAS key, or provenance requirement.

Violation 3: L0 state persists in repo-root.
- `state/agent_state.json` is written by `save()` and mutated after routine runtime events.

Violation 4: L0 enters prompt authority.
- `build_model_request()` injects recent outputs and previous commands into planner context.
- This is acceptable as continuity only, but dangerous if planner output treats it as source truth.

Violation 5: L2 quarantine is not physical.
- `append_reasoning()` stores reasoning under `memory/` and vault projections.
- Retrieval does not currently read it, but no guard prevents future indexing.

Violation 6: Vault projection is coupled to canonical-looking channels.
- Evidence and reasoning projection notes are generated automatically.

Violation 7: Generated outputs can recursively re-enter memory.
- Model/planner responses become tool results.
- Tool results become L0 recent outputs, L1 history, pseudo-L4 evidence, and vault notes.
- Future model requests read L0 recent outputs.

## Eventual Split Targets

Ephemeral runtime adapter:
- `AgentMemory`
- `MemoryStore.save()`
- `set_current_task()`
- `update_cwd()`
- `record_command()`
- `record_result()`
- browser continuity fields in `record_result()`

Operational log adapter:
- `build_runtime_paths()` log path responsibilities
- `append_history()`
- `append_browser_event()`
- command log write in `ExecutionEngine._record_execution()`
- session/error log writes in `AgentRuntime`

Reasoning trace quarantine:
- `append_reasoning()`
- `AgentRuntime.log_reasoning_trace()`
- planner and unknown-response trace flows
- `obsidian_vault/Reasoning` projection as derivative output only

Provenance registry:
- `runtime/tools/epistemic_registry.py`
- `runtime/provenance_registry.json`
- provenance enrichment in `AOIAEpistemicKernel._enrich_evidence()`

Immutable evidence adapter:
- Future replacement for `append_evidence()`
- Kernel evidence capture policy
- CAS evidence objects and fingerprints
- Explicit rejection of `action_result` as evidence

Contradiction registry:
- `runtime/tools/epistemic_registry.py`
- `runtime/contradiction_registry.json`
- contradiction lookup in `AOIAEpistemicKernel`
- future append-only contradiction status events

Vault projection layer:
- `build_obsidian_vault_paths()`
- `append_vault_note()`
- `_append_channel_note()`
- `_vault_block()`
- all Obsidian file writes as derivative projection only

## Recommended Future Split Order

1. Stop L1-to-L4 promotion in executor.
2. Quarantine L2 physically and prevent retrieval indexing.
3. Extract L0 runtime state behind an ephemeral adapter.
4. Extract L1 operational logs behind an operational log adapter.
5. Replace `append_evidence()` with a strict evidence capture interface and CAS store.
6. Move vault generation behind a projection layer that cannot be read as authority.
7. Formalize append-only provenance evolution.
8. Formalize append-only contradiction events.
9. Add retrieval guard checks for allowed source layers.

## Highest-Risk Future Refactor Operations

Highest risk:
- Changing `executor._record_execution()` because it affects every tool action and replay trace.
- Changing `record_result()` because it affects prompt continuity and browser state.
- Changing `append_evidence()` because current callers do not supply full L4 metadata.
- Changing vault projection because tests currently expect vault initialization.
- Changing knowledge routing because there are two local routing paths: AOIA kernel and legacy `KnowledgeRouter`.

Medium risk:
- Moving path creation out of `memory.py`.
- Separating browser logs from runtime state.
- Moving token savings report out of `state/`.

Lower risk:
- Adding documentation-only layer labels.
- Adding non-runtime validation scripts later.
- Adding read-only reports that inspect current paths.

## Implementation Blockers

- No CAS evidence schema exists yet.
- No append-only provenance event schema exists yet.
- No contradiction event schema exists yet.
- No retrieval guard exists.
- No promotion policy exists for human-reviewed artifacts.
- Current tests expect `MemoryStore` to initialize vault paths.
- Current runtime passes `MemoryStore` directly into `ExecutionEngine`.
- Current `append_evidence()` has callers with incompatible evidence quality.

## Runtime Phase 2A Readiness

Runtime is not safe for Phase 2A implementation until the first future refactor explicitly removes or blocks the `action_result` to evidence flow.

Recommended readiness judgment:
- Phase 1B documentation: ready after these reports are accepted.
- Phase 2A implementation: not ready until cleanup policy for untracked `state/`, existing runtime output locations, and evidence schema is accepted.
