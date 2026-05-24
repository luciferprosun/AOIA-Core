# Memory Contamination Map

Status: forensic mapping only. No runtime changes made.

## CRITICAL risk zones

### 1. `runtime/tools/memory.py`

Responsibilities mixed in one class:

- runtime state persistence (`state/agent_state.json`)
- append-only history (`memory/history.jsonl`)
- evidence journaling (`memory/evidence_memory.jsonl`)
- reasoning traces (`memory/reasoning_trace.jsonl`)
- browser event logging (`logs/browser/*.jsonl`)
- Obsidian vault projection (`obsidian_vault/*`)
- session bootstrapping (`session_start` note)
- mutable state replay via `AgentMemory`

Why this is critical:

- evidence, reasoning, and operational history are persisted by the same adapter
- the same object both represents live runtime state and writes notebook-style projections
- `append_history()` writes to history JSONL and also to the vault note surface
- `append_evidence()` and `append_reasoning()` each have both JSONL storage and vault note side effects

### 2. `runtime/main.py`

Mixed authority in one module:

- prompt construction
- model request generation
- runtime state snapshot
- local route handling
- deterministic knowledge routing
- legacy knowledge routing
- orchestrated planning path
- execution loop
- session logging
- reasoning trace logging
- epistemic fallback / unknown handling

Why this is critical:

- `main.py` is currently the coordination hub and the policy hub
- it builds the model prompt from mutable runtime state
- it injects RHCSA context into both planning and reactive execution
- it records evidence from the epistemic kernel directly into memory

### 3. `runtime/adaptive_routing/epistemic_kernel.py`

Mixed but more bounded:

- provenance loading
- contradiction loading
- deterministic retrieval
- confidence scoring
- routing-depth selection
- manual review detection
- response formatting

Risk:

- retrieval and epistemic output formatting are coupled
- provenance/contradiction signals are merged into one output object

## HIGH risk zones

### `runtime/tools/memory_hats.py`

- active prompt overlay is persisted in `state/active_hat.json`
- overlay text is inserted into the runtime request payload
- this is a mutable prompt-shaping layer with durable state

### `runtime/orchestrator/knowledge_router.py`

- reads local RHCSA memory
- updates token savings report in `state/token_savings_report.json`
- still encodes local retrieval policy that overlaps with the epistemic kernel

### `runtime/providers/config.py`

- persists model selection to `state/model_config.json`
- persists provider chain to `state/providers.json`
- loads API env files into process environment
- performs cloud-provider fallback

### `runtime/orchestrator/gemini_gemma.py`

- mixes strategic planning, worker action generation, RHCSA context injection, and worker-memory replay
- still assumes a two-model split and a worker model path that is explicitly disabled in this build

## MEDIUM risk zones

### `runtime/webapp.py`

- shares one `AgentRuntime` instance across requests
- exposes model switching and prompt execution in one process
- thread lock reduces race risk but does not separate authority

### `runtime/router/local_router.py`

- conservative and narrow, but still executes commands directly
- performs folder creation and shell execution before model involvement

### `runtime/tools/executor.py`

- one class handles tool registry, approval, execution, result recording, and memory writes

### `runtime/tools/epistemic_registry.py`

- builds provenance and contradiction registries from every knowledge artifact
- safe in purpose, but foundational to all later routing decisions

## Contamination patterns

1. Operational logs become pseudo-evidence
   - `executor._record_execution()` writes the same action payload to command logs, history, evidence, and browser logs where applicable.

2. Reasoning becomes persistent memory
   - `main.log_reasoning_trace()` writes to `memory/reasoning_trace.jsonl`.
   - `emit_epistemic_unknown()` also writes reasoning to disk.

3. Notebook projection and runtime state are intertwined
   - `MemoryStore.append_vault_note()` writes note surfaces from live execution payloads.

4. Provider selection becomes durable state
   - `ProviderManager.switch_model()` persists model choice into `state/model_config.json`.

5. RHCSA retrieval and local routing overlap
   - `AOIAEpistemicKernel` and `KnowledgeRouter` both decide whether local evidence should answer before cloud reasoning.

## Risk summary

- **CRITICAL**: `runtime/tools/memory.py`, `runtime/main.py`
- **HIGH**: `runtime/providers/config.py`, `runtime/orchestrator/knowledge_router.py`, `runtime/orchestrator/gemini_gemma.py`, `runtime/tools/memory_hats.py`
- **MEDIUM**: `runtime/webapp.py`, `runtime/router/local_router.py`, `runtime/tools/executor.py`, `runtime/tools/epistemic_registry.py`

