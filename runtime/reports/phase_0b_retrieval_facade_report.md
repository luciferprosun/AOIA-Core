# PHASE 0B - RETRIEVAL FACADE CONTRACT INTEGRATION REPORT

## 1. Facade Created

YES.

Created:

- `runtime/retrieval/facade.py`

Canonical facade API:

```python
retrieve_linux_knowledge(query: str, max_results: int = 5, project_dir: Path | None = None) -> LinuxRetrievalResponse
```

Read-only compatibility helpers also exist for legacy CLI-style functions:

- `linux_library_status()`
- `linux_load_topic(topic, max_chars=12000)`
- `linux_low_level_results(mode, query, limit=10)`
- `linux_filter_by_topic(topic, query, limit=10)`

The canonical facade delegates to `LinuxRetrievalEngine` and preserves:

- structured response
- refusal behavior
- confidence score
- provenance payload
- bounded result count

The facade does not call external APIs, embeddings, vector databases, memory writes, evidence writes, or token savings writes.

## 2. Modules Patched

Modified for Phase 0B:

- `runtime/retrieval/facade.py`
- `runtime/retrieval/__init__.py`
- `runtime/commands/local_commands.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/knowledge/rhcsa_engine.py`
- `runtime/memory/rhcsa_context.py`
- `runtime/tools/rhcsa_search.py`
- `tests/test_facade_delegation.py`
- `tests/test_retrieval_facade_contract.py`
- `tests/test_no_direct_rhcsa_search_imports.py`

Pre-existing Phase 0A files remain in the same working tree:

- `runtime/retrieval/linux/graph_loader.py`
- `runtime/reports/contamination_guard_report.md`
- `runtime/reports/phase_0a_stabilization_report.md`
- `runtime/reports/phase_0a_forensic_execution_report.md`
- `tests/test_scoring_consistency.py`
- `tests/test_retrieval_refusal.py`
- `tests/test_provenance_attachment.py`
- `tests/test_memory_layer_isolation_smoke.py`

## 3. Direct rhcsa_search Imports Removed

Coordinator/runtime modules audited:

- `runtime/commands/local_commands.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/orchestrator/knowledge_router.py`
- `runtime/main.py`
- `runtime/memory/rhcsa_context.py`

Result:

- No direct `from tools.rhcsa_search` import remains in these files.
- No direct `import tools.rhcsa_search` import remains in these files.
- `local_commands.py` now calls facade compatibility helpers.
- `knowledge_router.py` now uses `retrieve_linux_knowledge()` by default.
- `epistemic_kernel.py` now uses `retrieve_linux_knowledge()` instead of instantiating `LinuxRetrievalEngine`.
- `memory/rhcsa_context.py` now uses facade compatibility helpers for command/example context.

Validation command:

```bash
rg -n "from tools\.rhcsa_search|import tools\.rhcsa_search" runtime/commands runtime/adaptive_routing runtime/orchestrator runtime/main.py runtime/memory -g '*.py'
```

Result: no matches.

## 4. Compatibility Wrappers Preserved

Preserved:

- `runtime/tools/rhcsa_search.py` public functions remain available.
- `runtime/knowledge/rhcsa_engine.py` remains import-compatible.
- `RHCSAKnowledgeEngine.deprecated = True` remains present.
- `KnowledgeRouter(..., engine=legacy_engine)` remains supported without importing `rhcsa_engine.py`.
- `/rhcsa` local commands remain available and now reach low-level search through the facade.

Compatibility note:

`rhcsa_search.py` is still an internal low-level search API. It now carries a module warning instructing coordinator, router, kernel, and runtime code to use `runtime.retrieval.facade` instead.

## 5. Remaining Unresolved Direct Retrieval Paths

Remaining by design:

- `runtime/retrieval/linux/retrieval_engine.py` still imports low-level search functions from `tools.rhcsa_search`.
- `runtime/retrieval/facade.py` still imports `tools.rhcsa_search` inside compatibility helper functions.
- `runtime/tools/rhcsa_search.py` still contains the low-level index/search implementation.
- Legacy tests still import `tools.rhcsa_search` directly to validate backward-compatible low-level behavior.

No coordinator/router/runtime module is currently allowed to import `rhcsa_search.py` directly.

## 6. Canonical Index Safety

Verified untouched:

- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/candidates/`

Validation command:

```bash
git diff -- runtime/knowledge/canonical/rhcsa_commands.json runtime/knowledge/index/command_index.json runtime/knowledge/candidates
```

Result: no diff.

Candidate promotion was not implemented.

## 7. Runtime Router Hook Status

No new runtime router hook was activated.

Facts:

- `runtime/main.py` does not import `retrieve_linux_knowledge`.
- `runtime/main.py` does not reference `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.
- Existing runtime knowledge routing remains structurally in place.
- The existing kernel/router internals now delegate through the facade instead of direct legacy retrieval paths.

This is a facade consolidation change, not a new runtime activation path.

## 8. Tests Added

Created:

- `tests/test_retrieval_facade_contract.py`
- `tests/test_no_direct_rhcsa_search_imports.py`

Updated:

- `tests/test_facade_delegation.py`

Coverage:

- facade exact command query returns structured result
- facade invalid query refuses
- facade result includes provenance
- facade does not write evidence memory
- `local_commands.py` no longer imports `rhcsa_search.py`
- `epistemic_kernel.py` delegates through facade
- facade works without `AIOA_ENABLE_LINUX_RETRIEVAL_V1`
- runtime router hook is not newly activated
- coordinator modules do not import low-level `rhcsa_search.py`
- deprecated `RHCSAKnowledgeEngine` delegates through facade

## 9. Test Results

Required tests:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_linux_retrieval -v
```

Result: PASS, 7 tests.

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest tests.test_retrieval_facade_contract -v
```

Result: PASS, 8 tests.

Extended stabilization suite:

```bash
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest \
  tests.test_linux_retrieval \
  tests.test_retrieval_facade_contract \
  tests.test_scoring_consistency \
  tests.test_retrieval_refusal \
  tests.test_provenance_attachment \
  tests.test_memory_layer_isolation_smoke \
  tests.test_facade_delegation \
  tests.test_rhcsa_retrieval \
  tests.test_no_direct_rhcsa_search_imports -v
```

Result: PASS, 35 tests.

## 10. Scope Compliance

COMPLIANT.

Forbidden actions check:

- Router hook activation: NO
- Canonical index modification: NO
- Candidate record modification: NO
- Candidate promotion: NO
- Memory architecture rewrite: NO
- Provider logic change: NO
- Orchestration redesign: NO
- Vector DB addition: NO
- Embedding addition: NO
- Agent/autonomous loop addition: NO
- Gemini/Gemma orchestrator reactivation: NO

## 11. Current Retrieval Surface

Canonical public path:

```text
runtime.retrieval.facade.retrieve_linux_knowledge()
  -> runtime.retrieval.linux.LinuxRetrievalEngine.retrieve()
  -> runtime.tools.rhcsa_search low-level deterministic indexes
```

Deprecated compatibility path:

```text
runtime.knowledge.rhcsa_engine.RHCSAKnowledgeEngine
  -> runtime.retrieval.facade.retrieve_linux_knowledge()
```

CLI compatibility path:

```text
/rhcsa local commands
  -> runtime.retrieval.facade compatibility helpers
  -> runtime.tools.rhcsa_search low-level functions
```

## 12. Recommended Next Phase

Recommended next phase:

Phase 0C - Runtime Router Contract Guard.

Technical justification:

The facade is now present and coordinator direct imports were removed, but runtime-wide behavior still needs contract-level guardrails before candidate promotion. The next phase should add feature-flag/router contract tests proving that the active runtime path uses only the facade-backed retrieval surface and cannot silently fall back to deprecated lookup modules.

Candidate promotion should remain blocked until Phase 0C proves the runtime consumer path is single, auditable, and guarded.
