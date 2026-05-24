# Contamination Guard Report

Phase: 0A - Contamination Guard + Retrieval Facade Stabilization

## Finding

`runtime/tools/executor.py::_record_execution()` did not directly write execution outputs to `append_evidence()` or provenance stores.

The active L1 -> pseudo-L4 contamination path existed in `runtime/main.py::handle_knowledge_route()`:

```text
AOIA kernel retrieval decision
  -> kernel_decision.evidence
  -> memory_store.append_evidence("aoia_kernel_evidence", ...)
  -> runtime/memory/evidence_memory.jsonl
  -> Obsidian Evidence note
```

This path promoted runtime retrieval references into the evidence channel. It was not shell stdout/stderr directly, but it still wrote runtime-derived operational material into an L4-like store.

## Minimal Fix Applied

`handle_knowledge_route()` now writes the same retrieval reference payload to:

```text
memory_store.append_reasoning("aoia_kernel_evidence_reference", ...)
```

This preserves auditability without promoting runtime retrieval decisions into evidence memory.

## Evidence Writes Blocked

Execution artifacts remain allowed in:

- command logs
- history log
- session log
- reasoning trace where appropriate

Execution artifacts are not allowed in:

- `append_evidence()`
- `runtime/memory/evidence_memory.jsonl`
- Obsidian `Evidence/` notes
- provenance stores

## Validation

Added smoke test:

```text
tests/test_memory_layer_isolation_smoke.py
```

Verified:

```text
ExecutionEngine.execute(...)
  -> command/history logging
  -> no evidence_memory.jsonl creation
```

## Remaining Risks

- `MemoryStore.append_evidence()` still exists for future real source ingestion; it is not redesigned in this phase.
- Runtime code can still call `append_evidence()` in future changes unless guarded by tests/review.
- Full L2/L4 technical separation is still policy-level and should be enforced in a later memory authority split.

