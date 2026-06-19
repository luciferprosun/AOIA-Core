# AOIA Phase 0B — Evidence Boundary Formalization Report

## Summary

Phase 0B formalized the evidence boundary that was already partially introduced in the previous checkpoint.

The change is intentionally narrow:
- `MemoryStore.append_evidence()` now enforces a documented evidence write contract.
- Evidence writes require an explicit kind, source, and fingerprint.
- Invalid evidence payloads are rejected before any evidence record is appended.
- The public `MemoryStore` API is now covered by governance invariant tests.

This is a doctrine-to-enforcement transition, not a redesign.

## Files changed

- `runtime/tools/memory.py`
- `tests/test_evidence_boundary.py`
- `tests/test_evidence_write_contract.py`
- `docs/governance/EVIDENCE_WRITE_CONTRACT.md`
- `docs/governance/GOVERNANCE_IMPLEMENTATION_STATUS.md`
- `docs/stabilization/PHASE_0B_EVIDENCE_BOUNDARY_FORMALIZATION_REPORT.md`

## Governance invariant strengthened

The runtime doctrine that "evidence is a privileged epistemic event" is now enforced at the public memory boundary.

What is now runtime-enforced:
- only `aoia_kernel_evidence` may enter the evidence channel
- only allowed source domains may be used
- fingerprints are mandatory
- runtime action results cannot be promoted through the generic evidence API
- provider and browser-originated content cannot be promoted through the generic evidence API

This does not yet create a full provenance system. It only closes the public write path.

## Tests added or updated

Added:
- `tests/test_evidence_write_contract.py`

Existing coverage exercised again:
- `tests.test_evidence_boundary`
- `tests.test_executor_containment`
- `tests.test_memory_layer_isolation_smoke`
- `tests.test_retrieval_facade_contract`
- `tests.test_runtime_router_contract_guard`

## Test results

`pytest` is not installed in this environment:

```text
python3 -m pytest -q tests/test_evidence_boundary.py tests/test_evidence_write_contract.py tests/test_memory_layer_isolation_smoke.py
/usr/bin/python3: No module named pytest
```

Equivalent focused `unittest` validation passed:

```text
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_memory_layer_isolation_smoke
Ran 14 tests in 0.191s
OK

PYTHONPATH=runtime:. python3 -m unittest -v tests.test_evidence_boundary tests.test_executor_containment tests.test_memory_layer_isolation_smoke tests.test_retrieval_facade_contract tests.test_runtime_router_contract_guard
Ran 24 tests in 0.296s
OK
```

## What was deliberately not changed

- routing logic
- provider selection
- runtime execution semantics
- retrieval contract
- LSC/MHLM theory
- GUI/dashboard
- autonomous orchestration

## Remaining gaps

- append-only cryptographic provenance
- replay verification
- physical L3/L4 separation
- contradiction blocking
- epistemic approval gate
- browser provenance boundary
- model switch context hashing

## Recommended next phase

AOIA Phase 0C — Append-Only Provenance Log Skeleton
