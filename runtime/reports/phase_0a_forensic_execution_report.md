# PHASE 0A - FORENSIC EXECUTION REPORT

## 1. Executive Summary

Contamination path confirmed: YES

Contamination guard applied: YES

Retrieval scoring unified: PARTIAL

Facade delegation completed: PARTIAL

Dangerous drift remains: YES

Findings:

- Confirmed active pseudo-L4 write path existed in `runtime/main.py::handle_knowledge_route()`, not in `runtime/tools/executor.py::_record_execution()`.
- Applied minimal guard by moving AOIA kernel retrieval references from `append_evidence()` to `append_reasoning()`.
- Unified scoring constants for retrieval and low-level RHCSA search in `runtime/retrieval/linux/scoring.py`.
- Deprecated `runtime/knowledge/rhcsa_engine.py` and replaced its implementation with a compatibility wrapper over `LinuxRetrievalEngine`.
- Reduced `runtime/adaptive_routing/epistemic_kernel.py` to delegate retrieval to `LinuxRetrievalEngine`.
- Dangerous drift remains because `runtime/tools/rhcsa_search.py` is still an internal low-level search implementation and `runtime/commands/local_commands.py` still imports it directly for CLI commands.

## 2. Files Modified

Modified:

- `runtime/main.py`
- `runtime/tools/memory.py`
- `runtime/tools/rhcsa_search.py`
- `runtime/knowledge/rhcsa_engine.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/retrieval/linux/retrieval_engine.py`
- `runtime/retrieval/linux/scoring.py`

Created:

- `runtime/retrieval/linux/graph_loader.py`
- `runtime/reports/contamination_guard_report.md`
- `runtime/reports/phase_0a_stabilization_report.md`
- `runtime/reports/phase_0a_forensic_execution_report.md`
- `tests/test_scoring_consistency.py`
- `tests/test_retrieval_refusal.py`
- `tests/test_provenance_attachment.py`
- `tests/test_memory_layer_isolation_smoke.py`
- `tests/test_facade_delegation.py`

Deprecated:

- `runtime/knowledge/rhcsa_engine.py`

Deprecation marker:

```python
deprecated = True
RHCSAKnowledgeEngine.deprecated = True
```

## 3. Contamination Investigation

L1 -> pseudo-L4 contamination existed: YES

Exact offending flow:

```text
AgentRuntime.handle_knowledge_route(user_input)
  -> self.aoia_kernel.evaluate(user_input)
  -> kernel_decision.evidence
  -> self.memory_store.append_evidence("aoia_kernel_evidence", payload)
  -> runtime/memory/evidence_memory.jsonl
  -> runtime/obsidian_vault/Evidence/<session>.md
```

Exact functions involved:

- `runtime/main.py::AgentRuntime.handle_knowledge_route`
- `runtime/tools/memory.py::MemoryStore.append_evidence`
- `runtime/tools/memory.py::MemoryStore._append_channel_note`

Exact write path:

- `runtime/memory/evidence_memory.jsonl`
- `runtime/obsidian_vault/Evidence/<session>.md`

Important negative finding:

`runtime/tools/executor.py::_record_execution()` was inspected. It writes operational events to command logs, history, recent runtime outputs, and browser-event logs. It did not directly call `append_evidence()` and did not directly insert execution stdout/stderr into provenance stores.

Before behavior:

```text
Kernel retrieval references were written to the evidence channel.
```

After behavior:

```text
Kernel retrieval references are written to the reasoning channel:
MemoryStore.append_reasoning("aoia_kernel_evidence_reference", payload)
```

Exact minimal fix applied:

`runtime/main.py::handle_knowledge_route()` changed from:

```python
self.memory_store.append_evidence("aoia_kernel_evidence", ...)
```

to:

```python
self.memory_store.append_reasoning("aoia_kernel_evidence_reference", ...)
```

Whether runtime operational logs can still become evidence:

PARTIAL RISK REMAINS. No active runtime call to `append_evidence()` remains outside the `MemoryStore.append_evidence()` method itself, but the method still exists and can be called by future code. Technical prevention is not complete until evidence writes are source-ingestion-gated.

Whether shell outputs are isolated now:

YES for the inspected execution path. `ExecutionEngine.execute()` followed by `_record_execution()` does not create `evidence_memory.jsonl`; this is covered by `tests/test_memory_layer_isolation_smoke.py`.

Remaining unresolved contamination risks:

- `MemoryStore.append_evidence()` remains public.
- Memory authority separation is still not enforced by separate stores.
- Reasoning traces and history logs are still writable runtime artifacts and require future guardrails before any retrieval ingestion pipeline is added.

## 4. Retrieval Consolidation Status

`runtime/retrieval/linux/retrieval_engine.py`

Status: active canonical facade

Role:

- Owns deterministic Linux/RHCSA retrieval behavior.
- Supports exact, alias, subcommand, category, command family, keyword, low-confidence refusal.
- Attaches provenance to answered results.
- Uses `runtime/tools/rhcsa_search.py` as an internal low-level index/search adapter.
- Uses `runtime/retrieval/linux/graph_loader.py` for command graph loading.

`runtime/knowledge/rhcsa_engine.py`

Status: deprecated compatibility wrapper

Removed:

- Internal scoring function.
- Internal confidence function.
- Direct workflow/example/troubleshooting aggregation logic.
- Direct command graph matching implementation.

Now delegates:

```text
RHCSAKnowledgeEngine.retrieve_operational_memory(query)
  -> LinuxRetrievalEngine.retrieve(query)
```

Compatibility preserved:

- `KnowledgeHit` remains available.
- `RHCSAKnowledgeEngine.format_local_answer()` remains available.
- Existing import in `runtime/orchestrator/knowledge_router.py` still works.

`runtime/adaptive_routing/epistemic_kernel.py`

Status: delegated orchestration layer

Removed:

- Direct calls to `exact_command_lookup`.
- Direct calls to `search_rhcsa`.
- Direct calls to `grep_rhcsa`.
- Direct calls to `search_by_tag`.
- Internal score interpretation based on local RHCSA search result sets.

Now delegates:

```text
AOIAEpistemicKernel.evaluate(query)
  -> LinuxRetrievalEngine.retrieve(query)
  -> pressure/depth/manual-review/contradiction handling
```

Preserved:

- `select_depth()` pressure/depth flow.
- contradiction-hit reporting.
- manual review semantics.
- response shape.
- `KernelDecision` public object.

`runtime/tools/rhcsa_search.py`

Status: internal-only low-level search adapter, not deprecated yet

Remaining duplicate logic:

- Markdown module indexing.
- Exact command lookup over local modules/examples.
- Tag search.
- Grep-style literal search.
- Workflow/example retrieval helpers.

Reason retained:

`LinuxRetrievalEngine` still depends on these functions as deterministic low-level index access. Removing or wrapping it fully in this phase would create a larger refactor and risk breaking CLI commands and existing tests.

Remaining direct callers:

- `runtime/retrieval/linux/retrieval_engine.py`
- `runtime/commands/local_commands.py`
- `runtime/memory/rhcsa_context.py`
- `tests/test_rhcsa_retrieval.py`

## 5. Scoring Consistency Audit

Previous scoring differences:

- `runtime/retrieval/linux/scoring.py` defined retrieval facade scores and refusal threshold.
- `runtime/tools/rhcsa_search.py` used local hard-coded scores:
  - exact module match: `100`
  - exact example match: `95`
  - tag module match: `50`
  - tag example match: `45`
  - grep score unit: `match_count * 10`
- `runtime/knowledge/rhcsa_engine.py` had separate aggregation scoring and confidence labels based on workflows, commands, examples, troubleshooting, related topics, and graph matches.
- `runtime/adaptive_routing/epistemic_kernel.py` had separate confidence interpretation based on exact results and best result score.

New canonical scoring source:

```text
runtime/retrieval/linux/scoring.py
```

Systems now using `scoring.py`:

- `runtime/retrieval/linux/retrieval_engine.py`
- `runtime/adaptive_routing/epistemic_kernel.py`
- `runtime/tools/rhcsa_search.py`

Thresholds unified:

PARTIAL

Unified:

- refusal threshold: `REFUSAL_THRESHOLD = 30`
- facade confidence labels through `confidence_for(score)`
- exact/alias/subcommand/category/family/keyword/low-confidence scores
- low-level exact/tag/example/grep constants

Not fully unified:

- `runtime/orchestrator/knowledge_router.py` still has its own confidence rank comparison for deciding local handling thresholds.
- `runtime/commands/local_commands.py` still exposes legacy CLI paths over `rhcsa_search.py`.

Confidence labels unified:

PARTIAL

Unified for:

- `LinuxRetrievalEngine`
- `AOIAEpistemicKernel`
- deprecated `RHCSAKnowledgeEngine` wrapper

Not fully unified for:

- `KnowledgeRouter._meets_threshold()`, which still maps `none/low/medium/high` locally.

Refusal behavior consistent:

PARTIAL

Consistent inside:

- `LinuxRetrievalEngine`
- deprecated `RHCSAKnowledgeEngine` wrapper
- `AOIAEpistemicKernel` for no-evidence model fallback

Not runtime-wide:

- Runtime router is not yet wired to `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.
- `runtime/commands/local_commands.py` still returns raw search outputs for CLI commands.

## 6. Shared Graph Loader

Created:

```text
runtime/retrieval/linux/graph_loader.py
```

`@lru_cache` added:

YES

Implementation:

```python
@lru_cache(maxsize=4)
def load_command_graph(project_dir: str | Path | None = None) -> dict[str, Any]:
    ...
```

Systems now using it:

- `runtime/retrieval/linux/retrieval_engine.py`
- `runtime/knowledge/rhcsa_engine.py`

Duplicate graph loading still exists:

NO active duplicate command graph file read was found in the stabilized paths. `rhcsa_engine.py` no longer performs its own JSON graph read.

## 7. Tests Added

`tests/test_scoring_consistency.py`

Purpose:

- Verify exact lookup uses canonical exact score.
- Verify `LinuxRetrievalEngine` confidence score matches canonical threshold logic.
- Verify refusal threshold behavior comes from one source.

Status: PASS

`tests/test_retrieval_refusal.py`

Purpose:

- Verify unresolved queries refuse in `LinuxRetrievalEngine`.
- Verify deprecated `RHCSAKnowledgeEngine` preserves refusal score.
- Verify `AOIAEpistemicKernel` does not route locally without evidence.

Status: PASS

`tests/test_provenance_attachment.py`

Purpose:

- Verify every answered retrieval result has provenance keys:
  - `source_file`
  - `source_page`
  - `canonical_source`
  - `confidence_score`

Status: PASS

`tests/test_memory_layer_isolation_smoke.py`

Purpose:

- Verify `ExecutionEngine.execute()` does not create `evidence_memory.jsonl` for runtime execution results.

Status: PASS

`tests/test_facade_delegation.py`

Purpose:

- Verify `RHCSAKnowledgeEngine.retrieve_operational_memory()` delegates to `LinuxRetrievalEngine.retrieve()`.
- Verify `RHCSAKnowledgeEngine.deprecated` marker exists.

Status: PASS

Test command executed:

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
Ran 26 tests in 0.276s
OK
```

## 8. Remaining Risks

- `runtime/tools/memory.py` is still a transitional monolith.
- `MemoryStore.append_evidence()` still exists as a public method.
- Evidence vs reasoning separation is not yet technically sealed by separate stores or typed write gates.
- `runtime/tools/rhcsa_search.py` still contains low-level retrieval/indexing implementation.
- `runtime/commands/local_commands.py` still imports and calls `rhcsa_search.py` directly.
- `runtime/orchestrator/knowledge_router.py` still has local confidence-threshold logic.
- Runtime router is not yet feature-flagged to use the canonical retrieval facade.
- Candidate records are still unpromoted and unreviewed.
- Gemini Expansion Additions remain staged and must not be promoted without manual verification.
- Contradiction registry behavior remains partial and should not be described as complete.

## 9. Scope Compliance Check

Router hook activation: COMPLIANT - no runtime router hook was activated.

Canonical index modification: COMPLIANT - no diff in:

- `runtime/knowledge/canonical/rhcsa_commands.json`
- `runtime/knowledge/index/command_index.json`
- `runtime/knowledge/candidates/candidate_command_index.json`

Candidate promotion: COMPLIANT - no candidate promotion script or canonical update was implemented.

Memory architecture rewrite: COMPLIANT - only warning header and one write-channel change were added.

Provider logic changes: COMPLIANT - no provider files were modified.

Orchestration redesign: COMPLIANT - no Gemini/Gemma orchestrator behavior was changed.

Vector DB additions: COMPLIANT - none added.

Embedding additions: COMPLIANT - none added.

Overall scope status: COMPLIANT

## 10. Git/Diff Summary

Tracked files modified:

```text
7
```

Tracked diff stat at report time:

```text
7 files changed, 107 insertions(+), 166 deletions(-)
```

New untracked Phase 0A files:

- `runtime/retrieval/linux/graph_loader.py`
- `runtime/reports/contamination_guard_report.md`
- `runtime/reports/phase_0a_stabilization_report.md`
- `runtime/reports/phase_0a_forensic_execution_report.md`
- `tests/test_scoring_consistency.py`
- `tests/test_retrieval_refusal.py`
- `tests/test_provenance_attachment.py`
- `tests/test_memory_layer_isolation_smoke.py`
- `tests/test_facade_delegation.py`

Existing unrelated untracked artifact:

- `reports/forensic_export/`

Rollback simplicity:

YES

Reason:

- Phase 0A changes are localized to retrieval facade delegation, scoring constants, a single write-channel change, reports, and tests.
- No canonical indexes were modified.
- No provider behavior was modified.
- No router hook was activated.

Compatibility preserved:

YES, with caveat.

Preserved:

- `RHCSAKnowledgeEngine`
- `KnowledgeHit`
- `RHCSAKnowledgeEngine.retrieve_operational_memory()`
- `RHCSAKnowledgeEngine.format_local_answer()`
- `tools.rhcsa_search` public functions
- existing RHCSA retrieval tests

Caveat:

- The semantic payload of `RHCSAKnowledgeEngine` is now facade-derived and no longer reproduces its old multi-bucket workflow/example/troubleshooting aggregation.

## 11. Recommended Next Phase

Recommended next phase:

```text
Phase 0B - Retrieval Facade Contract Integration
```

Technical justification:

- Candidate promotion is still premature because `runtime/commands/local_commands.py` and `KnowledgeRouter` can still access older surfaces.
- The canonical retrieval facade now exists and has compatibility wrappers, but runtime-level routing contracts are not yet proven.
- Phase 0B should add feature flag plumbing and integration tests for `AIOA_ENABLE_LINUX_RETRIEVAL_V1` without changing default runtime behavior.
- Only after that should candidate promotion triage begin, because there will be a single proven consumer of promoted data.

Phase 0B should do exactly this:

1. Add narrow feature-flag plumbing for `AIOA_ENABLE_LINUX_RETRIEVAL_V1`.
2. Prove runtime local Linux/RHCSA route uses `LinuxRetrievalEngine` when the flag is on.
3. Prove default-off behavior preserves current runtime behavior.
4. Add tests preventing `rhcsa_engine.py` from regaining retrieval implementation logic.
5. Do not promote candidates.

