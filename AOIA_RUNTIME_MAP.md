# AOIA Runtime Map

Date: 2026-08-25

Mode: canonical runtime map

## Entrypoints

- `runtime/main.py`: canonical CLI and `AgentRuntime`.
- `runtime/webapp.py`: loopback-only web/API adapter over the same runtime.
- `runtime/run.sh`: CLI launcher.
- `runtime/run_web.sh`: web launcher.
- `tui/app.py`: optional Textual adapter over `AgentRuntime.run_text_request()`.

## Request branches

### Assistant and tool branch

1. operator input
2. `runtime/commands/` slash-command check
3. local fast route via `runtime/router/local_router.py`
4. epistemic route via `runtime/adaptive_routing/epistemic_kernel.py`
5. compatibility knowledge route via `runtime/orchestrator/knowledge_router.py`
6. optional model planning via `runtime/providers/`
7. structured action validation
8. operator approval where required
9. execution via `runtime/tools/executor.py`
10. state/provenance handling via bounded runtime tools

### Dated-evidence branch

1. `/review`, `GET /api/review/scenario`, or `POST /api/review`
2. `runtime/evidence_review/scenario.py`
3. `runtime/evidence_review/engine.py`
4. deterministic findings and SHA-256 bindings
5. `HUMAN_REVIEW_REQUIRED`

This branch has no provider, executor, persistence, or outbound-network dependency.

## Dependency map

```text
CLI / Web / TUI
  |
  +--> AgentRuntime
  |      +--> CommandRegistry
  |      +--> LocalRouter
  |      +--> AOIAEpistemicKernel
  |      +--> KnowledgeRouter -> retrieval facade
  |      +--> ProviderManager
  |      +--> ExecutionEngine
  |      `--> MemoryStore
  |
  `--> EvidenceReview
         +--> bundled scenario copy
         `--> deterministic engine
```

## Canonical modules

### Runtime control

- `runtime/main.py`
- `runtime/commands/`
- `runtime/webapp.py`

### Evidence review

- `runtime/evidence_review/__init__.py`
- `runtime/evidence_review/scenario.py`
- `runtime/evidence_review/engine.py`

### Routing and retrieval

- `runtime/router/local_router.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/retrieval/facade.py`
- `runtime/orchestrator/knowledge_router.py` (compatibility)
- `runtime/knowledge/`

### Execution

- `runtime/tools/executor.py`
- `runtime/tools/filesystem_tools.py`
- `runtime/tools/shell_tools.py`
- `runtime/tools/browser_tools.py`
- `runtime/tools/project_scanner.py`

### Providers

- `runtime/providers/config.py`
- `runtime/providers/aureon_provider.py`
- `runtime/providers/gemini_provider.py`
- `runtime/providers/openai_compatible.py`

### Memory, evidence, provenance, and contradiction handling

- `runtime/runtime_paths.py`
- `runtime/tools/memory.py`
- `runtime/tools/provenance.py`
- `runtime/tools/provenance_readout.py`
- `runtime/tools/epistemic_registry.py`
- `runtime/provenance_registry.json`

Mutable runtime state defaults to `~/.local/state/aoia`, not the source checkout.

## Authority map

| Artifact or component | Authority |
| --- | --- |
| Operator approval | Required authority for gated actions |
| Validated executor action | May execute only within its documented contract |
| Local retrieval result | Evidence-bearing only with attached provenance and applicable confidence boundaries |
| Dated-evidence review result | Metadata only; always requires human review |
| External model output | Suggestion only; not evidence or truth |
| Provenance/hash record | Local lineage and integrity only |
| Historical/research documentation | Context only; not runtime authority |

## Transitional zones

1. `runtime/orchestrator/` remains imported but is a compatibility surface, not a second authority.
2. `runtime/adaptive_routing/` combines canonical gating with non-canonical routing research.
3. `runtime/tools/memory.py` still owns several state responsibilities pending a future split.
4. Historical documentation and forensic exports preserve prior analysis and may describe older layouts.

## Current status

- runtime spine: canonical
- operator surfaces: unified over AOIA-Core
- dated-evidence review: implemented and bounded
- runtime isolation: partial
- structural stability: partial, covered by the repository test suite
