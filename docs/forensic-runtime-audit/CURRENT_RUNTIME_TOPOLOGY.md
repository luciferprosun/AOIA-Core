# Current Runtime Topology

Status: forensic mapping only. No runtime changes made.

## Runtime entrypoints

- [`runtime/main.py`](../../runtime/main.py) is the primary terminal entrypoint.
- [`runtime/webapp.py`](../../runtime/webapp.py) is the web entrypoint.
- [`runtime/run.sh`](../../runtime/run.sh) and [`runtime/run_web.sh`](../../runtime/run_web.sh) are thin launch wrappers.
- [`runtime/install.sh`](../../runtime/install.sh) is a bootstrap/install helper.

## High-level flow

The live runtime follows this path:

`user input -> command registry -> local router / epistemic kernel / knowledge router -> provider manager -> model request -> JSON validation -> executor -> memory + logs -> transcript/status`

The important split is:

- local fast-path handling in `runtime/main.py`
- deterministic RHCSA retrieval in `runtime/adaptive_routing/epistemic_kernel.py`
- legacy RHCSA routing in `runtime/orchestrator/knowledge_router.py`
- cloud-provider fallback in `runtime/providers/config.py`
- action dispatch in `runtime/tools/executor.py`

## Import graph

### Core runtime

- `runtime/main.py`
  - `commands.build_command_registry`
  - `adaptive_routing.epistemic_kernel.AOIAEpistemicKernel`
  - `memory.rhcsa_context.inject_linux_context`
  - `orchestrator.GeminiGemmaOrchestrator`
  - `orchestrator.knowledge_router.KnowledgeRouter`
  - `providers.ProviderManager`
  - `router.LocalRouter`
  - `tools.executor.ExecutionEngine`
  - `memory.gemma_worker_memory.GemmaWorkerMemory`
  - `tools.memory_hats.MemoryHatStore`
  - `tools.memory.MemoryStore`
  - `tools.system_info.detect_desktop_dir`
  - `tools.validator.extract_json_object`, `validate_action`

### Routing and retrieval

- `runtime/router/local_router.py` handles trivial local commands.
- `runtime/adaptive_routing/epistemic_kernel.py` performs deterministic RHCSA retrieval and contradiction-aware output.
- `runtime/orchestrator/knowledge_router.py` performs legacy local-memory routing for Linux operational requests.
- `runtime/tools/rhcsa_search.py` is the deterministic keyword/tag/exact/grep retrieval engine.

### Execution and persistence

- `runtime/tools/executor.py` dispatches tool actions and records execution.
- `runtime/tools/memory.py` owns runtime state, append-only logs, browser logs, and Obsidian vault projection.
- `runtime/tools/memory_hats.py` stores active context overlays in `memory/hats` and `state/active_hat.json`.
- `runtime/tools/epistemic_registry.py` builds provenance and contradiction registries.

### Providers

- `runtime/providers/config.py` owns model selection, env loading, provider fallback, and provider instantiation.
- `runtime/providers/gemini_provider.py`, `runtime/providers/aureon_provider.py`, `runtime/providers/openai_compatible.py` are provider adapters.

### Web

- `runtime/webapp.py` wraps `AgentRuntime` in a threaded HTTP service.

## Write paths

### Mutable runtime state

- `state/agent_state.json`
- `state/model_config.json`
- `state/providers.json`
- `state/active_hat.json`
- `state/token_savings_report.json`
- `state/browser_profile/`

### Runtime memory and logs

- `memory/history.jsonl`
- `memory/evidence_memory.jsonl`
- `memory/reasoning_trace.jsonl`
- `memory/hats/*.json`
- `logs/sessions/*.jsonl`
- `logs/commands/*.json`
- `logs/errors/*.json`
- `logs/browser/*.jsonl`
- `screenshots/*`

### Obsidian projection layer

- `obsidian_vault/Daily/*.md`
- `obsidian_vault/Sessions/*.jsonl`
- `obsidian_vault/Evidence/*.md`
- `obsidian_vault/Reasoning/*.md`
- `obsidian_vault/Logs/`
- `obsidian_vault/.obsidian/app.json`

### Knowledge and registry files

- `runtime/provenance_registry.json`
- `runtime/contradiction_registry.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/context/context_pack.json`
- `runtime/knowledge/injection/injected_context.json`
- `runtime/knowledge/parsed/rhcsa_sections.json`
- `runtime/knowledge/examples/*.json`
- `runtime/knowledge/raw/rhcsa_raw.txt`

## Read paths

- `runtime/main.py` reads prompt template, current state, provider status, local RHCSA context, knowledge routing, and epistemic flags.
- `runtime/providers/config.py` reads `state/model_config.json`, `state/providers.json`, and API env files under `~/.config/*/api.env`.
- `runtime/adaptive_routing/epistemic_kernel.py` reads the provenance and contradiction registries plus all RHCSA knowledge artifacts.
- `runtime/tools/rhcsa_search.py` reads the local RHCSA knowledge modules and example indexes.
- `runtime/tools/memory.py` reads/writes the same state and projection files on each step.

## Mutable state locations

The following locations are mutable and currently mixed with source-facing runtime code:

- `runtime/tools/memory.py` state + logs + vault projection
- `runtime/tools/memory_hats.py` overlays stored under `memory/hats`
- `runtime/providers/config.py` model/provider configuration persistence
- `runtime/adaptive_routing/epistemic_kernel.py` registry loading
- `runtime/orchestrator/knowledge_router.py` local savings report
- `runtime/webapp.py` shared runtime object in process memory

## Forensic notes

- `runtime/main.py` is not a thin coordinator yet; it contains prompt construction, routing, execution, logging, status, planning, orchestration, and local bootstrap logic.
- `runtime/tools/memory.py` mixes runtime state, evidence, reasoning, browser tracking, and Obsidian note generation.
- `runtime/providers/config.py` mixes configuration loading, provider fallback policy, model selection persistence, and provider instantiation.
- `runtime/orchestrator/knowledge_router.py` overlaps with `runtime/adaptive_routing/epistemic_kernel.py` on local RHCSA routing.
- `runtime/orchestrator/gemini_gemma.py` is still a delegated-plan path and still imports RHCSA context plus worker memory.
- `runtime/tools/build_rhcsa_library.py` still references `memory/rhcsa_context.py` as an integration point, which is not present as a runtime module in this tree.

