# AOIA Phase 0C — Append-Only Provenance Report

## Summary

Phase 0C adds a minimal append-only provenance skeleton with SHA-256 hash chaining.

The implementation is intentionally small:
- a dedicated provenance append layer was added
- provenance entries now include `timestamp`, `event_type`, `payload_hash`, `prev_hash`, and `entry_hash`
- the public append API only appends and does not expose a silent overwrite path
- the new behavior is covered by governance invariant tests

This phase does not attempt full replay, distributed trust, or immutable storage.

## Files changed

- `runtime/tools/provenance.py`
- `tests/test_append_only_provenance.py`
- `docs/governance/APPEND_ONLY_PROVENANCE_CONTRACT.md`
- `docs/governance/GOVERNANCE_IMPLEMENTATION_STATUS.md`
- `docs/stabilization/PHASE_0C_APPEND_ONLY_PROVENANCE_REPORT.md`

## New invariants

Enforced by the new append-only provenance skeleton:
- provenance writes append new records instead of replacing old ones
- each entry carries a SHA-256 `payload_hash`
- each entry links to the prior entry via `prev_hash`
- first entry uses a clean genesis previous hash
- invalid payloads fail before any partial append
- repeated appends preserve prior entries

## Test results

`pytest` is not installed in this environment:

```text
python3 -m pytest -q \
  tests/test_evidence_boundary.py \
  tests/test_evidence_write_contract.py \
  tests/test_append_only_provenance.py \
  tests/test_memory_layer_isolation_smoke.py \
  tests/test_retrieval_facade_contract.py \
  tests/test_runtime_router_contract_guard.py
/usr/bin/python3: No module named pytest
```

Equivalent focused `unittest` validation passed:

```text
PYTHONPATH=runtime:. python3 -m unittest -v tests.test_append_only_provenance tests.test_evidence_boundary tests.test_evidence_write_contract tests.test_memory_layer_isolation_smoke tests.test_retrieval_facade_contract tests.test_runtime_router_contract_guard
Ran 41 tests in 0.430s
OK
```

## What was deliberately NOT changed

- routing
- providers
- orchestration
- GUI
- LSC/MHLM theory
- replay engine
- SQLite migration
- distributed provenance

## Remaining gaps

- replay verification
- immutable storage
- provider authenticity verification
- browser provenance boundary
- contradiction enforcement
- epistemic approval
- physical memory isolation

## Recommended next phase

AOIA Phase 0D — Provenance Verification and Replay Read Path
