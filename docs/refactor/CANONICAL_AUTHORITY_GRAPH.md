# Canonical Authority Graph

Status: Phase 1C canonical authority freeze
Mode: forensic architecture only
Scope: AOIA-Core authority semantics before containment implementation

## Purpose

AOIA-Core must distinguish runtime continuity from epistemic authority.

This document freezes what is allowed to become authority, what must never become authority, and how authority may propagate through the system. It does not authorize implementation, refactor, runtime modification, adapter extraction, provider changes, routing changes, retrieval guards, or governance code.

## Canonical Authority Hierarchy

Highest authority is not "latest runtime output". Authority is constrained by source lineage, immutable evidence, and unresolved contradiction pressure.

Canonical order:

1. L3 provenance records
2. L5 contradiction registry
3. L4 immutable evidence
4. RHCSA deterministic knowledge artifacts
5. operator approvals for execution permission only
6. L2 reasoning traces for audit only
7. L1 operational logs for replay only
8. L0 runtime state for continuity only
9. vault projections for human readability only

Interpretation:
- L3 provenance defines source identity and constrains whether evidence can be trusted structurally.
- L5 contradictions constrain confidence and must remain visible.
- L4 evidence supports claims only when linked to provenance and contradiction checks.
- RHCSA deterministic knowledge can seed retrieval because it is source material under provenance policy.
- Operator approvals authorize actions; they do not create factual truth.
- L2, L1, L0, and vault projections are not factual authority.

## Objects That Are Authority

L3 provenance registry:
- `runtime/provenance_registry.json`
- Authority class: source lineage and artifact identity.
- Authority limit: does not itself prove the factual content of a claim; it identifies source origin, metadata, references, and fingerprints.

L5 contradiction registry:
- `runtime/contradiction_registry.json`
- Authority class: unresolved conflict and epistemic pressure.
- Authority limit: does not decide truth automatically; it constrains confidence and review requirements.

L4 immutable evidence:
- Future strict evidence objects only.
- Authority class: factual support artifact.
- Authority limit: valid only when fingerprinted, immutable, and linked to provenance.
- Current `memory/evidence_memory.jsonl` is not canonical L4 because it contains mixed payloads.

RHCSA deterministic knowledge:
- `runtime/knowledge/**`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/command_graph.json`
- Authority class: deterministic local knowledge source material.
- Authority limit: must be interpreted through provenance, contradiction checks, retrieval policy, and confidence boundaries.

Operator approvals:
- Authority class: permission authority for execution.
- Authority limit: approval means "this action may run"; it does not mean the action result is true evidence, provenance, or contradiction resolution.

## Objects That Are Never Authority

The following must never become provenance, immutable evidence, retrieval source material, or contradiction resolution authority:

- L0 runtime state.
- `AgentMemory`.
- `state/agent_state.json`.
- `recent_outputs`.
- `previous_commands`.
- `current_task`.
- current working directory.
- browser state.
- open tabs.
- current browser URL.
- screenshots.
- session continuity.
- L1 operational logs.
- command logs.
- session logs.
- browser logs.
- error logs.
- command outputs.
- tool outputs.
- approval prompts or approval rejections.
- L2 reasoning traces.
- planner reasoning.
- planner summaries.
- model/provider responses.
- cloud planner output.
- local planner output.
- generated summaries.
- temporary summaries.
- Obsidian vault notes.
- vault daily notes.
- vault session notes.
- vault evidence projection notes.
- vault reasoning projection notes.

These objects may be useful for continuity, audit, debugging, or human review. They are not authority.

## Authority Propagation Rules

| Flow | Status | Rule |
| --- | --- | --- |
| L3 provenance -> L4 evidence | allowed | Evidence may reference provenance; provenance constrains evidence identity. |
| L4 evidence -> retrieval | allowed | Only valid immutable, fingerprinted, provenance-linked evidence may feed retrieval. |
| L5 contradiction -> retrieval confidence | allowed | Contradictions constrain confidence and review; they do not auto-resolve truth. |
| RHCSA deterministic knowledge -> provenance | allowed | Source artifacts may be registered as provenance through deterministic build policy. |
| RHCSA deterministic knowledge -> retrieval | allowed | Retrieval may read deterministic knowledge under provenance and contradiction policy. |
| Operator approval -> execution | allowed | Approval authorizes action execution only. |
| Operator approval -> evidence | forbidden | Approval is not factual evidence. |
| L0 runtime state -> L4 evidence | forbidden | Continuity state is not evidence. |
| L0 runtime state -> provenance | forbidden | Runtime state cannot define source lineage. |
| L0 runtime state -> retrieval source | forbidden | Runtime state is not source material. |
| L1 logs -> L4 evidence | forbidden | Operational logs are procedural records. |
| L1 logs -> provenance | forbidden | Logs are not source identity. |
| L1 logs -> retrieval source | forbidden | Replay traces are not retrieval authority. |
| L2 reasoning -> L4 evidence | forbidden | Reasoning is generated inference, not evidence. |
| L2 reasoning -> provenance | forbidden | Reasoning cannot create source lineage. |
| L2 reasoning -> retrieval source | forbidden | Retrieval over reasoning traces creates recursive authority. |
| Runtime output -> evidence | forbidden | Tool/model outputs need external provenance before evidence capture. |
| Planner summary -> provenance | forbidden | Generated summaries are derivatives, not source identity. |
| Cloud planner output -> evidence | forbidden by default | External provenance is required before evidence capture. |
| Vault projection -> retrieval source | forbidden | Vault is derivative projection only. |
| Vault projection -> evidence | forbidden | Projection is not immutable evidence. |
| Screenshot -> evidence | forbidden by default | Screenshot requires explicit capture policy, fingerprint, source link, and evidence type. |
| Command output -> evidence | forbidden by default | Command output is L1 unless recaptured through a source/evidence policy. |

## Safe Authority Flow

Canonical safe flow:

```text
external or deterministic source
  -> source ingestion / knowledge artifact
  -> L3 provenance record
  -> L5 contradiction check
  -> L4 immutable evidence object
  -> retrieval guard
  -> answer construction with confidence constraints
```

Properties required:
- Source identity is explicit.
- Source fingerprint is present.
- Contradictions remain visible.
- Evidence is immutable.
- Retrieval reads only allowed authority layers.
- Generated answer does not rewrite provenance, evidence, or contradiction state.

## Forbidden Authority Flow

Canonical forbidden flow:

```text
runtime output
  -> history log
  -> evidence_memory.jsonl
  -> retrieval
  -> authority claim
```

This flow is forbidden because:
- Runtime output is not source lineage.
- History is L1, not L4.
- Current evidence memory is mixed and not canonical.
- Retrieval must not read runtime logs or reasoning traces.
- Authority claims must be constrained by provenance and contradiction checks.

Expanded forbidden flow:

```text
planner output
  -> action JSON
  -> tool result
  -> recent_outputs
  -> next prompt
  -> generated summary
  -> vault note
  -> future retrieval or knowledge ingestion
```

This flow is forbidden as authority propagation. It may exist as continuity and projection, but it must not become evidence, provenance, or retrieval source material.

## Runtime-Only Components

Runtime-only components maintain execution continuity. They may influence the next action as context, but they must not define factual authority.

Runtime-only:
- `runtime/tools/memory.py` current L0 state responsibilities.
- `AgentMemory`.
- `MemoryStore.save()`.
- `MemoryStore.record_command()`.
- `MemoryStore.record_result()`.
- `MemoryStore.set_current_task()`.
- `MemoryStore.update_cwd()`.
- browser state fields.
- `AgentRuntime.build_model_request()` runtime state block.
- `AgentRuntime.snapshot_status()`.

Rule:
- Runtime-only components may support planning context and status reporting.
- Runtime-only components must not write L3, L4, or L5 authority.

## Operational-Only Components

Operational-only components record what happened. They support replay, audit, and debugging.

Operational-only:
- `ExecutionEngine._record_execution()` command log behavior.
- `MemoryStore.append_history()`.
- `MemoryStore.append_browser_event()`.
- `AgentRuntime.log_session_event()`.
- `AgentRuntime.log_error()`.
- `logs/commands/**`.
- `logs/browser/**`.
- `logs/sessions/**`.
- `logs/errors/**`.
- `memory/history.jsonl`.

Rule:
- Operational-only components may write L1.
- Operational-only components must not write L4.
- Operational-only components must not feed retrieval as source material.

## Epistemic-Only Components

Epistemic-only components evaluate source-backed knowledge, evidence candidates, uncertainty, and contradictions.

Epistemic-only:
- `runtime/adaptive_routing/epistemic_kernel.py`.
- `runtime/tools/rhcsa_search.py`.
- `runtime/knowledge/rhcsa_engine.py`.
- deterministic knowledge artifacts under `runtime/knowledge/**`.
- reasoning trace emitters when used only for audit.

Rule:
- Epistemic components may read L3/L4/L5 where policy allows.
- Epistemic components may emit L2 reasoning traces.
- Epistemic components must not promote L2 to L4.
- Epistemic components must not auto-resolve L5.

## Projection-Only Components

Projection-only components create human-readable surfaces. They are not canonical memory.

Projection-only:
- `obsidian_vault/**`.
- `MemoryStore.build_obsidian_vault_paths()` behavior.
- `MemoryStore.append_vault_note()`.
- `MemoryStore._append_channel_note()`.
- `MemoryStore._vault_block()`.
- vault daily notes.
- vault session notes.
- vault evidence notes.
- vault reasoning notes.

Rule:
- Projection-only components may display or summarize.
- Projection-only components must not feed provenance.
- Projection-only components must not feed evidence.
- Projection-only components must not feed retrieval indexes.
- Projection-only components must be treated as derivative and non-authoritative.

Vault semantics:
- The Obsidian vault is projection-only.
- It is not operational memory authority.
- It is not an evidence layer.
- It is not a provenance source.
- It is a forbidden retrieval source unless a future human-reviewed source ingestion policy explicitly imports an external source artifact, not the vault note itself.

## Governance-Only Components

Governance-only components define rules, constraints, and permissions. They do not create factual evidence by themselves.

Governance-only:
- future authority registry.
- future retrieval guard.
- future evidence promotion policy.
- future human-review promotion policy.
- operator approvals as execution permissions.
- memory doctrine documents.

Rule:
- Governance can permit, block, or classify flows.
- Governance cannot turn generated output into source truth.
- Governance cannot erase contradictions silently.
- Governance cannot make L0/L1/L2 authority by declaration.

## Canonical Role Of Current Components

`runtime/tools/memory.py`:
- Current role: mixed runtime persistence, logs, reasoning traces, evidence-like writes, and vault projection.
- Canonical future role: not authority itself.
- Authority status now: unsafe mixed memory surface.

`runtime/tools/executor.py`:
- Current role: action dispatcher and execution recorder.
- Canonical role: operational execution and L1 replay only.
- Authority status now: unsafe because `_record_execution()` writes action results into evidence-like memory.

`runtime/adaptive_routing/epistemic_kernel.py`:
- Current role: deterministic local epistemic kernel.
- Canonical role: epistemic evaluator reading provenance, contradictions, and deterministic knowledge.
- Authority status now: comparatively healthy, but its evidence output lands in weak storage.

`runtime/orchestrator/knowledge_router.py`:
- Current role: legacy local RHCSA router and token-savings reporter.
- Canonical role: transitional retrieval path, operationally useful but not final authority boundary.
- Authority status now: must remain secondary to canonical kernel/governance model.

`runtime/provenance_registry.json`:
- Current role: source identity registry.
- Canonical role: L3 provenance authority.
- Authority status now: valid seed, but not append-only event history.

`runtime/contradiction_registry.json`:
- Current role: conflict and duplicate-source registry.
- Canonical role: L5 contradiction authority.
- Authority status now: valid seed, with no auto-resolution observed.

`runtime/knowledge/**`:
- Current role: deterministic RHCSA/Linux knowledge source corpus.
- Canonical role: source material eligible for provenance, contradiction checks, evidence creation, and retrieval.
- Authority status now: allowed source surface under guard policy.

## Must Never Enter L4

The following must never enter canonical L4 evidence:
- `action_result` payloads.
- tool outputs.
- command outputs.
- shell stdout/stderr.
- command success/failure status.
- browser events.
- browser state.
- screenshots without evidence capture policy.
- runtime state.
- recent outputs.
- previous commands.
- planner output.
- cloud provider output.
- local model output.
- reasoning traces.
- vault notes.
- generated summaries.
- session logs.
- approval events.
- rejection events.
- temporary reports.

Allowed exception:
- An external artifact observed through a tool may become L4 only through a future explicit evidence capture policy requiring source identity, fingerprint, capture time, evidence type, and provenance linkage.

## Must Never Enter Provenance

The following must never enter L3 provenance:
- runtime state.
- operational logs.
- command outputs.
- reasoning traces.
- planner summaries.
- provider responses.
- vault notes.
- generated reports.
- screenshots without source identity.
- temporary summaries.
- operator approval events.
- token savings reports.

Allowed source identity must come from:
- deterministic source ingestion.
- knowledge artifact registration.
- external source artifact capture with identity and fingerprint.
- human-reviewed source registration under policy.

## Must Never Enter Retrieval Indexes

The following must never be indexed as source material:
- `state/**`.
- `logs/**`.
- `memory/history.jsonl`.
- `memory/reasoning_trace.jsonl`.
- mixed `memory/evidence_memory.jsonl`.
- `obsidian_vault/**`.
- `screenshots/**` unless evidence policy creates a separate L4 object.
- session continuity records.
- planner traces.
- model responses.
- vault projections.
- temporary generated summaries.
- command output logs.

Retrieval may read:
- deterministic knowledge artifacts.
- L3 provenance.
- canonical L4 evidence once implemented.
- L5 contradictions as confidence and review constraints.

## Future Enforcement Implications

This document implies future enforcement work, but does not implement it.

Future enforcement must:
- block `action_result` from evidence writes.
- prevent retrieval from indexing L0/L1/L2/projection paths.
- require provenance and fingerprint for L4.
- distinguish operator approval from factual authority.
- label vault output as projection-only.
- keep contradiction records append-only and visible.
- prevent generated summaries from becoming provenance.
- prevent cloud planner output from becoming evidence without external provenance.
- treat legacy mixed `memory/evidence_memory.jsonl` as quarantined until reviewed.

## Runtime Safety Judgment

Runtime is not currently authority-safe.

Runtime is safe for Phase 2A pseudo-evidence containment only if Phase 2A is narrowly scoped to containment of the known bad flow:

```text
ExecutionEngine._record_execution()
  -> MemoryStore.append_evidence("action_result", payload)
```

Phase 2A must not broaden into memory splitting, provider changes, routing changes, governance implementation, or retrieval redesign until this authority graph is accepted.

## Frozen Decision

The canonical AOIA authority graph is:

```text
source artifact
  -> L3 provenance
  -> L5 contradiction check
  -> L4 immutable evidence
  -> retrieval guard
  -> answer construction
```

Everything else is continuity, operation, reasoning audit, projection, or governance policy. None of those are factual authority unless explicitly and validly promoted through future provenance/evidence policy.
