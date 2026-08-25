# AOIA-Core Architecture

## System boundary

AOIA-Core has one canonical runtime tree under `runtime/`. The CLI, local web console, optional TUI, deterministic retrieval, dated-evidence review, provider abstraction, execution tools, memory, and provenance helpers are interfaces or modules of that system. They are not independent products or authority domains.

## Request topology

```text
Operator input
  |
  +--> dated-evidence route (/review or /api/review)
  |      -> bounded input validator
  |      -> immutable scenario copy
  |      -> deterministic matcher + SHA-256 binding
  |      -> findings
  |      -> HUMAN_REVIEW_REQUIRED
  |
  +--> normal runtime route
         -> slash-command registry
         -> deterministic local router
         -> AOIA epistemic kernel / retrieval facade
         -> legacy knowledge-router compatibility path
         -> optional provider planning
         -> structured action validation
         -> operator approval where required
         -> local executor
         -> result and bounded state/provenance updates
```

The evidence-review branch does not enter provider planning or the executor. Assistant model selection does not affect its output.

## Operator surfaces

| Surface | Entrypoint | Delegates to |
| --- | --- | --- |
| CLI | `runtime/run.sh` / `runtime/main.py` | `AgentRuntime`, command registry, evidence-review engine |
| Web | `runtime/run_web.sh` / `runtime/webapp.py` | `AgentRuntime` plus the same evidence-review engine |
| TUI | `scripts/start_tui.sh` / `tui/app.py` | `AgentRuntime.run_text_request()` |

The web server serves the repository-level `web/` assets, binds only to loopback, lazily initializes the provider runtime, and makes the deterministic review endpoints available without a provider or API key.

## Canonical modules

### Runtime control

- `runtime/main.py`: request loop, safeguards, routing order, provider planning, and tool loop.
- `runtime/commands/`: deterministic slash commands executed before provider routing.
- `runtime/webapp.py`: one local HTTP/static adapter.

### Dated evidence review

- `runtime/evidence_review/scenario.py`: isolated bundled registry and official-source metadata.
- `runtime/evidence_review/engine.py`: input validation, deterministic comparison, findings, hashes, and operator summary.

The module always returns `HUMAN_REVIEW_REQUIRED` and `METADATA_ONLY_NO_AUTHORITY`. See `docs/modules/DATED_EVIDENCE_REVIEW.md` and ADR-006.

### Routing and retrieval

- `runtime/router/local_router.py`: deterministic fast path for obvious local requests.
- `runtime/adaptive_routing/epistemic_kernel.py`: canonical epistemic gate.
- `runtime/retrieval/facade.py`: canonical Linux knowledge boundary.
- `runtime/orchestrator/knowledge_router.py`: compatibility path that delegates through the facade.
- `runtime/knowledge/`: static RHCSA corpus, indexes, validators, and source artifacts.

### Providers

- `runtime/providers/`: optional external model adapters and one `ProviderManager`.

Provider output is non-deterministic and non-authoritative. Provider selection is an assistant-routing setting, not a change to evidence or execution authority.

### Execution

- `runtime/tools/executor.py`: dispatch and approval boundary.
- `runtime/tools/filesystem_tools.py`, `shell_tools.py`, and `browser_tools.py`: controlled local capabilities.
- `runtime/tools/project_scanner.py`: bounded project inspection.

### Memory, evidence, and provenance

- `runtime/tools/memory.py`: transitional memory/state facade.
- `runtime/runtime_paths.py`: external mutable-state root (`AOIA_HOME` or `~/.local/state/aoia`).
- `runtime/tools/provenance.py`: append-only provenance records and verification.
- `runtime/tools/epistemic_registry.py`: provenance/contradiction registry generation.

Recorded lineage and hashes establish integrity relationships, not factual truth.

## Authority boundaries

Canonical runtime responsibilities:

- route input through documented deterministic and optional provider paths,
- validate structured actions,
- request operator approval where required,
- execute allowed local tools,
- keep evidence, reasoning, execution results, and provider output distinct,
- refuse or require review when confidence/authority is insufficient.

Non-authoritative inputs and outputs include:

- external model text,
- dated-review findings and hashes,
- tool output before explicit evidence classification,
- historical reports and forensic exports,
- research and case-study documentation.

## Known transitional areas

- `runtime/orchestrator/` retains compatibility code and is not a second canonical authority.
- `runtime/adaptive_routing/` contains both the canonical epistemic kernel and research-oriented classifiers.
- `runtime/tools/memory.py` remains a transitional facade with multiple state responsibilities.
- historical documentation duplicates older structural descriptions and is not runtime authority.

## Integration rule

Any new classifier, scenario type, provider behavior, or authority-affecting route requires a documented input/output contract, focused tests, explicit limitations, and operator approval before activation. ADR-006 records that approval and the bounded contract for dated-evidence review.
