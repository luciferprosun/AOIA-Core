# Memory Contamination Graph

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: contamination and leakage around `runtime/tools/memory.py`

## Core Contamination Graph

```text
tool action result
  -> command log JSON                  [L1]
  -> AgentMemory.recent_outputs         [L0]
  -> memory/history.jsonl               [L1]
  -> memory/evidence_memory.jsonl       [pseudo-L4 violation]
  -> obsidian_vault/Daily               [projection]
  -> obsidian_vault/Sessions            [projection]
  -> model prompt recent_outputs        [recursive generated-output channel]
```

This is the highest-risk contamination graph in current AOIA-Core.

## L0 Leak Map

Current L0 sources:
- `AgentMemory.cwd`
- `AgentMemory.current_task`
- `AgentMemory.previous_commands`
- `AgentMemory.recent_outputs`
- `AgentMemory.open_tabs`
- `AgentMemory.current_browser_page`
- `AgentMemory.screenshots`
- `AgentMemory.browser_active`

Current leak paths:
- L0 is persisted to `state/agent_state.json`.
- L0 is read by `build_model_request()` and included in model prompt JSON.
- L0 is read by `snapshot_status()`.
- L0 is mixed into vault notes through `_vault_block()` because every block includes `cwd` and `task`.
- L0 browser state is mutated from tool result payloads.

Doctrine risk:
- L0 is allowed as continuity state, but it must not persist as authority.
- Current prompt injection makes L0 influential over planner behavior.
- Current vault projection can make L0 look like durable continuity memory.

## L1 Leak Map

Current L1 sources:
- `logs/commands/<timestamp>.json`
- `memory/history.jsonl`
- `logs/browser/browser_<session>.jsonl`
- `logs/sessions/session_<session>.jsonl`
- `logs/errors/error_<timestamp>.json`
- token savings report under `state/token_savings_report.json`

Current leak paths:
- `append_history()` writes L1 to `memory/history.jsonl` and then projects it into vault daily/session notes.
- `append_browser_event()` writes L1 browser logs and projects browser events into vault daily/session notes.
- `ExecutionEngine._record_execution()` writes the same payload to command logs, history, and evidence-like memory.

Doctrine risk:
- L1 must never become evidence.
- Current executor flow makes L1 action results become pseudo-L4.

## L2 Leak Map

Current L2 sources:
- `planner_request`
- `aoia_kernel_decision`
- `knowledge_route_disabled`
- `unknown_response`
- other calls through `AgentRuntime.log_reasoning_trace()`

Current leak paths:
- `append_reasoning()` writes to `memory/reasoning_trace.jsonl`.
- `append_reasoning()` writes to `obsidian_vault/Reasoning/<session>.md`.
- Direct calls to `append_reasoning()` can bypass helper-level safeguard checks.
- Human-readable reasoning projection may later be copied into knowledge or prompt contexts.

Doctrine risk:
- L2 must never become evidence.
- Retrieval does not currently read L2, but no retrieval guard prevents future reads.
- Vault projection creates a soft human-mediated route for L2 to re-enter authority channels.

## Pseudo-Evidence Formation

Pseudo-evidence forms at:

```text
ExecutionEngine._record_execution
  -> append_evidence("action_result", payload)
```

Payload includes:
- action requested
- result object
- command output when present
- filesystem path when present
- browser URL or text when present
- cancellation/rejection result when present
- current cwd

Why this violates Phase 1A:
- It has no external provenance requirement.
- It has no content fingerprint.
- It has no CAS identity.
- It has no evidence type schema.
- It may contain generated model action proposals.
- It may contain operational command output.
- It may contain approval rejection events.
- It is structurally indistinguishable from stronger evidence-like records in the same JSONL file.

## Runtime State Becomes Authority

Authority-like runtime state paths:
- Prompt construction includes `previous_commands` and `recent_outputs`.
- Prompt construction includes active browser page and open tabs.
- Prompt construction includes current vault path.
- Snapshot/status exposes memory state as runtime status.

Risk:
- The planner may infer truth from recent outputs.
- Recent model-generated output can become future prompt context.
- Runtime status can be mistaken for epistemic source state.

This is not a direct retrieval violation today, but it is a recursive planning contamination path.

## Generated Output Recursive Re-Entry

Recursive flow:

```text
cloud/local planner output
  -> action JSON
  -> executor result
  -> record_result()
  -> AgentMemory.recent_outputs
  -> build_model_request()
  -> next planner prompt
```

Expanded recursive flow:

```text
cloud/local planner output
  -> action result
  -> append_history()
  -> append_evidence("action_result")
  -> append_vault_note()
  -> human-readable notes
  -> possible future operator copy/paste or knowledge ingestion
```

Doctrine risk:
- Generated outputs must not become provenance.
- Cloud planner output must not become evidence without external provenance.
- Current runtime does not enforce this distinction.

## Vault Projection Contamination

Vault projection contamination paths:
- `session_start` becomes daily note and session JSONL.
- Every history event becomes daily note and session JSONL.
- Browser events become daily note and session JSONL.
- Evidence events become evidence markdown notes.
- Reasoning events become reasoning markdown notes.

Risk:
- Projection notes mix L0 cwd/task with L1/L2/pseudo-L4 payload summaries.
- Summaries use only `message`, `summary`, or `error`, which can hide source identity and context.
- Vault files look durable and human-readable, which increases risk of later misuse as source authority.

## Retrieval Contamination Status

Current retrieval sources:
- `runtime/knowledge/**`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/command_graph.json`
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

Current non-sources:
- `memory/history.jsonl`
- `memory/evidence_memory.jsonl`
- `memory/reasoning_trace.jsonl`
- `obsidian_vault/**`
- `logs/**`
- `state/agent_state.json`

Current judgment:
- Retrieval is not currently contaminated by L0/L1/L2 reads.
- Retrieval is still vulnerable because mutable runtime output directories live under the repository root and no guard prevents future indexing.

## Contamination Hotspots

Hotspot 1: `ExecutionEngine._record_execution()`
- Converts every action result into history and evidence.
- Highest immediate doctrine violation.

Hotspot 2: `MemoryStore.append_evidence()`
- Generic append with no evidence contract.
- Accepts both real artifact summaries and operational payloads.

Hotspot 3: `MemoryStore.record_result()`
- Stores compact result summaries in L0.
- Feeds prompt continuity.

Hotspot 4: `AgentRuntime.build_model_request()`
- Converts L0 state into planner context.
- Enables recursive generated-output influence.

Hotspot 5: `MemoryStore.append_vault_note()`
- Projects mixed runtime events into durable human-readable notes.

Hotspot 6: `MemoryStore.append_reasoning()`
- Persists L2 and projects it to vault.
- Quarantine is not enforced physically.

Hotspot 7: `KnowledgeRouter.record_local_hit()` and `record_miss()`
- Writes routing metrics under `state/`.
- Creates mutable retrieval-adjacent state outside `memory.py`.

## Current Behaviors Violating Phase 1A Doctrine

Violates "L1 must never become evidence":
- `append_evidence("action_result", payload)` from executor.

Violates "cloud planner output must not become evidence without external provenance":
- Model-proposed action results can be written as evidence-like events.

Violates "runtime state must not persist as authority":
- L0 state persists in `state/agent_state.json` and is prompt-visible.
- The violation becomes active if prompt consumers treat it as source truth.

Violates "L2 must never become evidence":
- No direct code path currently promotes L2 to evidence.
- Risk remains because L2 and pseudo-L4 live under the same generic memory concept and vault projection.

Violates "retrieval must not read L0/L1/L2":
- No current direct violation found.
- Enforcement is absent.

Violates "contradiction records must not be auto-resolved":
- Current kernel reports contradictions without auto-resolution.
- Current registry builder writes unresolved policy.
- No active violation found.

## Containment Recommendations For Future Implementation

- First remove or block `action_result` evidence writes.
- Give `append_evidence()` a replacement interface requiring source identity and fingerprint.
- Move L2 reasoning traces away from any retrieval-scannable path.
- Mark vault projection as derivative-only and prevent retrieval indexing.
- Keep command/session/browser logs as L1 only.
- Keep runtime state L0 behind a continuity adapter.
- Add a retrieval guard with explicit allowlist: L3, L4, and L5 constraints only.
