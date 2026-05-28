# Current Memory Flow

Date: 2026-05-23
Phase: Memory Ontology Foundation

## Current Runtime Memory Flow

Primary producers:
- `runtime/main.py`
- `runtime/tools/executor.py`
- `runtime/tools/memory.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/tools/epistemic_registry.py`

## Flow Map

### Session bootstrap

`MemoryStore.__init__()` creates and/or writes:
- `state/agent_state.json`
- `memory/history.jsonl`
- `memory/evidence_memory.jsonl`
- `memory/reasoning_trace.jsonl`
- `logs/browser/browser_<session>.jsonl`
- `obsidian_vault/**`

This means runtime mutability begins at startup, before any substantive reasoning.

### Action execution flow

1. `main.py` builds or receives an action
2. `executor.execute()` runs the action
3. `_record_execution()` writes:
   - command log JSON under `logs/commands/`
   - compact runtime result into in-memory session state
   - `append_history("action_result", payload)`
   - `append_evidence("action_result", payload)`
4. browser actions also call `append_browser_event(payload)`

Result:
- one executed action becomes both operational history and evidence

### Knowledge route flow

1. `AOIAEpistemicKernel.evaluate()` performs retrieval
2. kernel decision reasoning is written through `log_reasoning_trace()`
3. if kernel found evidence, `main.py` writes `append_evidence("aoia_kernel_evidence", ...)`
4. if kernel answers locally, response is emitted directly
5. otherwise `KnowledgeRouter` may still perform a second local decision

Result:
- evidence artifacts are identified at retrieval time
- reasoning about that evidence is stored separately
- legacy routing still sits behind the kernel

### Unknown / safeguard flow

When fallback uncertainty is triggered:
- `emit_epistemic_unknown()` logs reasoning through `append_reasoning()`
- no direct evidence object is created

Result:
- uncertainty itself becomes reasoning trace, not evidence

### Provenance and contradiction flow

`tools/epistemic_registry.py` builds:
- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`

These registries are loaded by:
- `AOIAEpistemicKernel`

Result:
- provenance and contradictions are currently committed registry snapshots, not per-session mutable traces

## Where Operational Logs Become Pseudo-Evidence

Main contamination point:
- `executor._record_execution()` writes every action result to both:
  - history
  - evidence

This means:
- shell output
- filesystem operations
- browser interactions
- approval-rejected actions

can be treated structurally like evidence, even when they are only operational traces.

## Where Reasoning Traces Leak Into Memory

Reasoning is intentionally separated into:
- `memory/reasoning_trace.jsonl`
- `obsidian_vault/Reasoning/`

Leak vector:
- `append_vault_note()` and `_vault_block()` produce human-readable summaries from mixed event sources
- daily notes can mix operational notes with reasoning-adjacent summaries

This creates soft semantic bleed between:
- operational event logging
- human continuity notes
- epistemic trace interpretation

## Where Mutable State Contaminates Authority

Repo-root contamination points:
- `state/`
- `memory/`
- `logs/`
- `screenshots/`
- `obsidian_vault/`

These are runtime outputs living inside source authority boundaries.

## Current Layer Approximation

- L0 candidate: `state/agent_state.json`, in-memory `AgentMemory`
- L1 candidate: `logs/**`, `memory/history.jsonl`
- L2 candidate: `memory/reasoning_trace.jsonl`, `obsidian_vault/Reasoning/`
- L3 candidate: `runtime/provenance_registry.json`
- L4 candidate: `memory/evidence_memory.jsonl`, retrieval artifacts, saved page text snapshots
- L5 candidate: `runtime/contradiction_registry.json`

## Current Flow Judgment

The current runtime already contains all six semantic classes in rough form, but they are not yet cleanly separated.

Biggest ambiguity:
- L1 operational logs and L4 evidence are still partially collapsed into the same write path
