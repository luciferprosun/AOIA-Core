# Memory Authority Boundaries

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: authority mapping for current `memory.py` split planning

## Boundary Principle

`memory.py` currently stores records, but it does not enforce authority. Phase 1A requires each memory layer to have an explicit authority class. Phase 1B identifies where current code crosses those authority classes.

## Current Authority Classes

| Current Surface | Intended Layer | Current Authority Problem |
| --- | --- | --- |
| `AgentMemory` | L0 | Prompt-visible continuity state can be mistaken for source context. |
| `state/agent_state.json` | L0 | Runtime state persists under repo root. |
| `memory/history.jsonl` | L1 | Operational history is projected into vault and duplicated into evidence. |
| `logs/commands/*.json` | L1 | Command replay records may contain stdout/stderr that look factual. |
| `logs/browser/*.jsonl` | L1 | Browser operations are not evidence captures by themselves. |
| `memory/reasoning_trace.jsonl` | L2 | Reasoning is persisted near evidence-like memory. |
| `runtime/provenance_registry.json` | L3 | Registry exists, but evolution is not append-only yet. |
| `memory/evidence_memory.jsonl` | pseudo-L4 | Generic evidence append accepts non-evidence payloads. |
| `runtime/contradiction_registry.json` | L5 | Registry exists, but runtime event semantics are not formalized yet. |
| `obsidian_vault/**` | projection | Human-readable derivatives can be mistaken for canonical memory. |

## Authority Graph

```text
runtime/knowledge/**
  -> provenance registry (L3)
  -> contradiction registry (L5)
  -> AOIAEpistemicKernel evidence candidates
  -> local answer construction

ExecutionEngine action result
  -> command log (L1)
  -> runtime state (L0)
  -> history log (L1)
  -> evidence_memory.jsonl (pseudo-L4 violation)
  -> vault projection

Reasoning event
  -> reasoning_trace.jsonl (L2)
  -> vault reasoning projection

Vault projection
  -> operator-readable notes
  -> must not feed provenance/evidence/retrieval
```

## Boundary Findings

Finding 1: L0 boundary is weak.
- `AgentMemory` is correctly shaped for ephemeral continuity.
- It is persisted and injected into prompts.
- It must later be explicitly marked as non-authoritative context.

Finding 2: L1 boundary is broken at executor evidence write.
- `action_result` is operational history.
- It is currently written to `memory/evidence_memory.jsonl`.
- This is the strongest violation of Phase 1A doctrine.

Finding 3: L2 boundary is documented but not enforced.
- Reasoning traces are separate from evidence writes.
- No retrieval path currently reads reasoning traces.
- Physical location and vault projection still allow future accidental misuse.

Finding 4: L3 boundary exists outside `memory.py`.
- Provenance registry has content hashes and artifact metadata.
- It is read by the AOIA kernel.
- It is not append-only event history yet.

Finding 5: L4 boundary does not exist as an implementation contract.
- `append_evidence()` is a generic write method.
- No required fingerprint, source reference, content-addressed key, or schema exists.
- Kernel evidence summaries and executor action results share the same storage path.

Finding 6: L5 boundary is healthier than L4 but incomplete.
- Contradictions are reported and not auto-resolved.
- Runtime contradiction status events do not yet exist.

Finding 7: Vault boundary is absent.
- Vault output is currently generated as a side effect.
- It is a projection, but code does not label it as derivative or non-authoritative.

## Future Adapter Classification

Ephemeral runtime adapter:
- Owns L0 state only.
- Should preserve active session continuity.
- Must not expose state as evidence, provenance, or retrieval source.
- Candidate current members: `AgentMemory`, `save()`, `set_current_task()`, `update_cwd()`, `record_command()`, `record_result()`.

Operational log adapter:
- Owns L1 event logs only.
- Should record chronological runtime behavior.
- Must not write evidence.
- Candidate current members: `append_history()`, `append_browser_event()`, command log path handling, session logs, error logs.

Reasoning trace quarantine:
- Owns L2 reasoning records only.
- Should store route choices, uncertainty, planner requests, kernel decisions, and unknown responses.
- Must not be indexed by retrieval.
- Candidate current members: `append_reasoning()`, `log_reasoning_trace()`.

Provenance registry:
- Owns L3 source identity and lineage.
- Should be append-only or versioned by epoch.
- Candidate current modules: `tools/epistemic_registry.py`, `runtime/provenance_registry.json`, kernel provenance enrichment.

Immutable evidence adapter:
- Owns L4 evidence objects only.
- Must require fingerprint, source identity, capture time, evidence type, and immutable write semantics.
- Candidate current member to replace: `append_evidence()`.

Contradiction registry:
- Owns L5 conflict records and status events.
- Must preserve unresolved conflicts and append status changes.
- Candidate current modules: `tools/epistemic_registry.py`, `runtime/contradiction_registry.json`, kernel contradiction hits.

Vault projection layer:
- Owns derivative human-readable notes.
- Must not be authority.
- Candidate current members: `build_obsidian_vault_paths()`, `append_vault_note()`, `_append_channel_note()`, `_vault_block()`.

## Future Split Safety Rules

Rule 1:
- Remove executor-to-evidence writes before changing evidence storage semantics.

Rule 2:
- Keep a compatibility facade while extracting adapters because `AgentRuntime`, `ExecutionEngine`, commands, and tests depend on `MemoryStore`.

Rule 3:
- Do not make retrieval aware of vault, history, reasoning, or runtime state.

Rule 4:
- Do not let evidence migration accept old `action_result` records as canonical L4 evidence.

Rule 5:
- Treat existing `memory/evidence_memory.jsonl` as legacy mixed memory until reviewed.

Rule 6:
- Treat vault notes as derivative projection and never as source lineage.

Rule 7:
- Keep contradiction detection report-only until an append-only status event model exists.

## Highest-Risk Refactor Boundaries

`ExecutionEngine._record_execution()`:
- Highest risk because it is called for every action and currently fans out to L0/L1/pseudo-L4.

`MemoryStore.append_evidence()`:
- High risk because current callers provide payloads with different epistemic quality.

`MemoryStore.record_result()`:
- High risk because prompt continuity depends on it.

`AgentRuntime.build_model_request()`:
- High risk because it determines how L0 state enters generated planning.

`build_runtime_paths()`:
- Medium risk because moving paths affects browser profiles, screenshots, logs, and state.

`build_obsidian_vault_paths()`:
- Medium risk because tests and `/vault` expect vault availability.

`KnowledgeRouter` state report:
- Medium risk because it writes retrieval metrics into `state/`, outside memory ownership.

## Phase 2A Gate

Runtime is not safe for Phase 2A implementation until the team accepts:
- the exact first change to stop `action_result` evidence writes
- the compatibility strategy for `MemoryStore`
- the fate of legacy `memory/evidence_memory.jsonl`
- the physical quarantine rule for L2
- the retrieval guard allowlist
- the handling policy for untracked runtime `state/`

Recommended Phase 2A starting point:
- a narrow change that prevents new L1 operational action results from entering evidence-like storage while preserving L1 history, command logs, L0 continuity, and existing tests.
