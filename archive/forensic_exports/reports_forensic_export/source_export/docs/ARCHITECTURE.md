# Architecture

## Current Runtime Flow

```text
User input
  -> local fast routes
  -> optional local knowledge retrieval
  -> model planning
  -> structured action validation
  -> human approval for non-response actions
  -> local executor
  -> memory/log update
  -> final response or next step
```

## Existing Architectural Layers

Local interface:
- terminal CLI through `run.sh`
- optional local web UI through `run_web.sh`

Runtime core:
- `AgentRuntime` in `main.py`
- builds prompt context
- manages model interaction
- coordinates execution results

Execution:
- `tools/executor.py`
- shell/filesystem/browser actions
- validation and safety checks

Knowledge:
- `knowledge/rhcsa_engine.py`
- `tools/rhcsa_search.py`
- local Linux/RHCSA lookup before external reasoning

Providers:
- `providers/`
- OpenRouter/Gemini/OpenAI-compatible configuration
- should remain isolated from AOIA until explicit integration

Memory and logs:
- `memory/`
- `state/`
- `logs/`
- `obsidian_vault/`

## AOIA Target Shape

AOIA should become a local advisory layer before provider selection or heavy
reasoning. It should eventually observe local conditions and recommend a mode.

Early target:

```text
local conditions
  -> AOIA classifiers
  -> recommended routing mode
  -> runtime policy decision
```

Current status:

```text
AOIA files exist
  -> no runtime integration
  -> no provider integration
  -> no autonomous behavior
```

## Design Boundary

AOIA should not execute actions. It should only classify conditions and propose
local mode hints until a later approved step.

Examples of future AOIA inputs:
- local hour
- static regional traffic profile
- token budget
- local cache confidence
- provider availability
- user-declared urgency

Examples of future AOIA outputs:
- `deep_mode`
- `surface_mode`
- `high_traffic`
- `low_traffic`
- later: `defer_heavy_work`, `prefer_local_cache`, `allow_external_reasoning`

## Integration Rule

No AOIA classifier may affect runtime behavior until:

1. its input contract is documented,
2. its output contract is documented,
3. tests or manual validation exist,
4. a checkpoint exists,
5. the user explicitly approves integration.

