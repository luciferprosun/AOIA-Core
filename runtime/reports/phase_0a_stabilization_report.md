# Phase 0A Stabilization Report

Phase: Contamination Guard + Retrieval Facade Stabilization

## 1. Contamination Fix Status

Fixed the active evidence-channel write in `runtime/main.py::handle_knowledge_route()`.

Before:

```text
kernel_decision.evidence -> append_evidence("aoia_kernel_evidence", ...)
```

After:

```text
kernel_decision.evidence -> append_reasoning("aoia_kernel_evidence_reference", ...)
```

`runtime/tools/executor.py::_record_execution()` was inspected. It writes command logs, history, recent runtime outputs, and browser events. It does not call `append_evidence()`.

## 2. Scoring Consistency Status

`runtime/retrieval/linux/scoring.py` remains the canonical scoring module.

Added shared constants for legacy low-level RHCSA search scores:

- `TAG_MATCH_SCORE`
- `EXAMPLE_TAG_MATCH_SCORE`
- `EXAMPLE_EXACT_MATCH_SCORE`
- `GREP_MATCH_UNIT_SCORE`

Updated `runtime/tools/rhcsa_search.py` to use these constants instead of local magic numbers for exact, tag, example, and grep scoring.

## 3. Deprecated Modules Status

`runtime/knowledge/rhcsa_engine.py` is now a compatibility wrapper over `LinuxRetrievalEngine`.

Deprecation markers:

```text
deprecated = True
RHCSAKnowledgeEngine.deprecated = True
```

The module is retained to avoid breaking existing imports in `runtime/orchestrator/knowledge_router.py`.

## 4. Facade Delegation Status

`runtime/knowledge/rhcsa_engine.py` delegates operational retrieval through:

```text
runtime/retrieval/linux/retrieval_engine.py
```

`runtime/adaptive_routing/epistemic_kernel.py` now delegates RHCSA/Linux retrieval to `LinuxRetrievalEngine` and preserves:

- pressure/depth logic
- routing decision shape
- contradiction awareness
- manual review semantics
- kernel response format

## 5. Remaining Duplicate Retrieval Paths

Remaining by design for this phase:

- `runtime/tools/rhcsa_search.py`

This module remains as a low-level deterministic index/search adapter used by `LinuxRetrievalEngine`.

Reduced:

- `runtime/knowledge/rhcsa_engine.py` no longer owns retrieval logic.
- `runtime/adaptive_routing/epistemic_kernel.py` no longer directly calls `exact_command_lookup`, `grep_rhcsa`, `search_by_tag`, or `search_rhcsa`.

## 6. Unresolved Risks

- `MemoryStore.append_evidence()` is still available for real source ingestion and requires future guardrails.
- `runtime/tools/rhcsa_search.py` still contains low-level search implementation because the canonical retrieval engine depends on it.
- Runtime router is not yet hooked to the new retrieval facade behind `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.
- Candidate indexes remain staged only; no promotion logic was implemented.
- Full technical L2/L4 separation remains a future memory authority split.

## 7. Tests Added

- `tests/test_scoring_consistency.py`
- `tests/test_retrieval_refusal.py`
- `tests/test_provenance_attachment.py`
- `tests/test_memory_layer_isolation_smoke.py`
- `tests/test_facade_delegation.py`

## 8. Tests Passed

Focused stabilization suite:

```text
PYTHONPATH=runtime runtime/.venv/bin/python -m unittest \
  tests.test_scoring_consistency \
  tests.test_retrieval_refusal \
  tests.test_provenance_attachment \
  tests.test_memory_layer_isolation_smoke \
  tests.test_facade_delegation \
  tests.test_linux_retrieval \
  tests.test_rhcsa_retrieval -v
```

Result:

```text
Ran 26 tests in 0.589s
OK
```

Compile validation:

```text
PYTHONPATH=runtime runtime/.venv/bin/python -m py_compile \
  runtime/main.py \
  runtime/tools/memory.py \
  runtime/knowledge/rhcsa_engine.py \
  runtime/adaptive_routing/epistemic_kernel.py \
  runtime/retrieval/linux/scoring.py \
  runtime/retrieval/linux/graph_loader.py \
  runtime/retrieval/linux/retrieval_engine.py \
  runtime/tools/rhcsa_search.py
```

Result: OK.

## 9. Files Modified

- `runtime/main.py`
- `runtime/tools/memory.py`
- `runtime/tools/rhcsa_search.py`
- `runtime/knowledge/rhcsa_engine.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/retrieval/linux/retrieval_engine.py`
- `runtime/retrieval/linux/scoring.py`

Files added:

- `runtime/retrieval/linux/graph_loader.py`
- `runtime/reports/contamination_guard_report.md`
- `runtime/reports/phase_0a_stabilization_report.md`
- `tests/test_scoring_consistency.py`
- `tests/test_retrieval_refusal.py`
- `tests/test_provenance_attachment.py`
- `tests/test_memory_layer_isolation_smoke.py`
- `tests/test_facade_delegation.py`

## 10. Recommended Next Phase

Phase 0B should be a narrow integration contract phase:

1. Add feature flag plumbing for `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.
2. Add runtime-level tests proving the flag routes through `LinuxRetrievalEngine`.
3. Keep default off until integration tests pass.
4. Do not promote candidates until the runtime retrieval facade is the only active RHCSA/Linux consumer.

