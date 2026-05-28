# AOIA Dependency Graph

Date: 2026-05-23

## Top-Level Runtime Graph

```text
user
  -> runtime/main.py
      -> commands/build_command_registry
      -> router/LocalRouter
      -> adaptive_routing/AOIAEpistemicKernel
      -> orchestrator/KnowledgeRouter
      -> providers/ProviderManager
      -> tools/ExecutionEngine
      -> tools/MemoryStore
      -> tools/MemoryHatStore
      -> memory.rhcsa_context          [missing package in current repo]
      -> memory.gemma_worker_memory    [missing package in current repo]
```

## CLI Path

```text
main.py
  -> command registry
      -> local_commands.py
          -> rhcsa_search.py
          -> validator.py
```

## Local Deterministic Path

```text
main.py
  -> router/local_router.py
  -> adaptive_routing/epistemic_kernel.py
      -> adaptive_routing/deterministic_router.py
      -> tools/epistemic_registry.py
      -> tools/rhcsa_search.py
          -> runtime/knowledge/**
```

## Legacy Local Knowledge Path

```text
main.py
  -> orchestrator/knowledge_router.py
      -> knowledge/rhcsa_engine.py
          -> tools/rhcsa_search.py
```

## Model Planning Path

```text
main.py
  -> providers/ProviderManager
      -> gemini_provider.py
      -> openai_compatible.py
      -> aureon_provider.py
      -> gemma_provider.py
```

## Orchestrated Planning Path

```text
main.py
  -> orchestrator/gemini_gemma.py
      -> ProviderManager.generate_with_fallback()
      -> worker memory package [missing in current repo]
      -> memory hats
      -> validator
```

## Tool Execution Path

```text
main.py
  -> tools/executor.py
      -> shell_tools.py
      -> filesystem_tools.py
      -> browser_tools.py
      -> project_scanner.py
      -> tools/memory.py
```

## Web Path

```text
web/index.html
web/app.js
  -> runtime/webapp.py
      -> AgentRuntime
```

## Persisted State Surfaces

Created by `tools/memory.py` and related runtime execution:
- `state/`
- `memory/`
- `logs/`
- `screenshots/`
- `obsidian_vault/`

## Dependency Risks

### Missing dependency boundary

- `main.py` depends on an absent `memory` package
- this is the most serious structural gap in current AOIA-Core extraction

### Redundant dependency chains

- `epistemic_kernel -> rhcsa_search`
- `knowledge_router -> rhcsa_engine -> rhcsa_search`

This means deterministic local retrieval is represented twice at different abstraction layers.

### Experimental adjacency

- `adaptive_routing` contains both canonical and experimental components
- dependency graph does not clearly separate production-critical and research-only modules
