# Memory Dependency Graph

Status: Phase 1B forensic analysis
Mode: documentation only
Scope: current dependency structure around `runtime/tools/memory.py`

## Direct Module Dependencies

`runtime/tools/memory.py` imports:
- `datetime`
- `json`
- `dataclasses.asdict`
- `dataclasses.dataclass`
- `dataclasses.field`
- `pathlib.Path`
- `typing.Any`

It does not import runtime modules. The dependency direction is mostly inward: other runtime components depend on `MemoryStore`.

## Direct Runtime Dependents

`runtime/main.py`:
- Imports `MemoryStore`.
- Constructs it in `AgentRuntime.__init__()`.
- Reads `memory_store.memory`.
- Reads `memory_store.vault_dir`.
- Reads `memory_store.paths`.
- Calls `append_evidence()`.
- Calls `append_reasoning()` through `log_reasoning_trace()` and direct calls.

`runtime/tools/executor.py`:
- Imports `MemoryStore`.
- Receives a `MemoryStore` instance at construction.
- Reads `memory_store.memory.cwd`.
- Reads `memory_store.paths.command_logs_dir`.
- Reads `memory_store.paths.state_dir`.
- Reads `memory_store.paths.screenshots_dir`.
- Calls `record_command()`.
- Calls `record_result()`.
- Calls `append_history()`.
- Calls `append_evidence()`.
- Calls `append_browser_event()`.

`runtime/commands/local_commands.py`:
- Reads `runtime.memory_store.vault_dir` for `/vault`.

Tests:
- `tests/test_main.py` constructs `MemoryStore` directly and asserts vault initialization.
- `tests/test_epistemic_safeguards.py` constructs `MemoryStore` directly and asserts evidence/reasoning vault directories.

## Indirect Runtime Dependents

`AgentRuntime.build_model_request()`:
- Depends on `AgentMemory` shape.
- Injects `session_id`, `cwd`, `current_task`, `previous_commands`, `recent_outputs`, browser state, screenshots, and vault path into model prompt context.

`AgentRuntime.snapshot_status()`:
- Depends on `AgentMemory` and `MemoryStore` paths.
- Exposes L0 state and vault path to status callers.

`ExecutionEngine.configure_browser_bridge()`:
- Depends on `memory_store.paths.state_dir / "browser_profile"`.
- Depends on `memory_store.paths.screenshots_dir`.

`ExecutionEngine._record_execution()`:
- Depends on `memory_store.paths.command_logs_dir`.
- Depends on `MemoryStore` write methods.

## Path Dependency Graph

```text
project_dir
  -> state/
     -> agent_state.json
     -> browser_profile/
     -> model_config.json
     -> providers.json
     -> token_savings_report.json
  -> memory/
     -> history.jsonl
     -> evidence_memory.jsonl
     -> reasoning_trace.jsonl
  -> screenshots/
  -> logs/
     -> browser/
     -> sessions/
     -> commands/
     -> errors/
  -> obsidian_vault/
     -> Daily/
     -> Sessions/
     -> Evidence/
     -> Reasoning/
     -> .obsidian/app.json
     -> 00_START_HERE.md
```

The graph shows that mutable runtime output is physically inside the repository root. This is a source-authority contamination risk even when those paths are untracked.

## Function Dependency Graph

```text
MemoryStore.__init__
  -> build_runtime_paths
  -> build_obsidian_vault_paths
  -> save
  -> append_vault_note("session_start")

append_history
  -> memory/history.jsonl
  -> append_vault_note

append_evidence
  -> memory/evidence_memory.jsonl
  -> _append_channel_note(obsidian_vault/Evidence)

append_reasoning
  -> memory/reasoning_trace.jsonl
  -> _append_channel_note(obsidian_vault/Reasoning)

append_browser_event
  -> logs/browser/browser_<session>.jsonl
  -> append_vault_note("browser_event")

record_command
  -> AgentMemory.previous_commands
  -> save

record_result
  -> AgentMemory.recent_outputs
  -> AgentMemory.current_browser_page
  -> AgentMemory.open_tabs
  -> AgentMemory.browser_active
  -> AgentMemory.screenshots
  -> save

append_vault_note
  -> obsidian_vault/Daily/<date>.md
  -> obsidian_vault/Sessions/<session>.jsonl

_append_channel_note
  -> obsidian_vault/<Evidence|Reasoning>/<session>.md
```

## Execution Dependency Graph

```text
AgentRuntime
  -> MemoryStore
  -> ExecutionEngine(memory_store)
  -> LocalRouter
  -> KnowledgeRouter
  -> AOIAEpistemicKernel

ExecutionEngine.execute(action)
  -> tool handler
  -> _record_execution(action, result)
     -> logs/commands/<timestamp>.json
     -> MemoryStore.record_result(result)
     -> MemoryStore.append_history("action_result", payload)
     -> MemoryStore.append_evidence("action_result", payload)
     -> MemoryStore.append_browser_event(payload) for browser actions
```

This is the most important dependency path because one runtime action fans out into L0, L1, pseudo-L4, and vault projection.

## Knowledge Retrieval Dependency Graph

```text
AgentRuntime.handle_knowledge_route(user_input)
  -> AOIAEpistemicKernel.evaluate(user_input)
     -> exact_command_lookup
     -> search_rhcsa
     -> grep_rhcsa
     -> search_by_tag
     -> runtime/provenance_registry.json
     -> runtime/contradiction_registry.json
     -> KernelDecision(reasoning, evidence)
  -> MemoryStore.append_reasoning("aoia_kernel_decision", reasoning)
  -> MemoryStore.append_evidence("aoia_kernel_evidence", artifact summary)
  -> optional KnowledgeRouter.route(user_input, active_hat)
     -> RHCSAKnowledgeEngine.retrieve_operational_memory(user_input)
     -> state/token_savings_report.json
```

Retrieval currently reads deterministic knowledge files, provenance registry, contradiction registry, and command graph. It does not read `memory/history.jsonl`, `memory/reasoning_trace.jsonl`, or `obsidian_vault/**`.

## Authority Dependency Graph

```text
runtime/knowledge/** source files
  -> tools.rhcsa_search indexes
  -> AOIAEpistemicKernel evidence candidates

runtime/provenance_registry.json
  -> AOIAEpistemicKernel._provenance_by_artifact
  -> AOIAEpistemicKernel._enrich_evidence

runtime/contradiction_registry.json
  -> AOIAEpistemicKernel._duplicate_commands
  -> AOIAEpistemicKernel._contradiction_hits

KernelDecision.evidence
  -> AgentRuntime.handle_knowledge_route
  -> MemoryStore.append_evidence("aoia_kernel_evidence", summary)
```

The authority graph is healthier than the execution graph, but the final write into `append_evidence()` loses strict L3/L4 structure because the destination is a generic JSONL append.

## Reverse Dependency Risks

Risk 1:
- Future retrieval may accidentally index `memory/` or `obsidian_vault/` because they are in the repository root.

Risk 2:
- Prompt construction reads L0 recent outputs and previous commands. Generated output can therefore influence future generated output through state continuity.

Risk 3:
- Tests assert vault initialization through `MemoryStore`, which increases refactor blast radius.

Risk 4:
- `ExecutionEngine` depends on `MemoryStore` for paths and memory writes, so splitting `memory.py` requires a compatibility facade or staged extraction.

## Refactor Dependency Constraints

Must preserve during future implementation:
- `MemoryStore` construction behavior until tests are updated.
- `memory_store.paths` shape until executor/browser/session code is migrated.
- `memory_store.memory` shape until prompt/status code is migrated.
- `/vault` output behavior until local command contract is changed.
- Command log write behavior until operational log adapter exists.

Should not preserve as doctrine:
- `append_evidence("action_result", payload)`.
- Vault projection as a default side effect of all history events.
- Evidence writes without fingerprints or provenance links.
- L0 runtime output as prompt-visible authority.
